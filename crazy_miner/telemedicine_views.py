import requests
from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404, render
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
import random
import os
from rest_framework import status, permissions
from django.http import FileResponse
import logging
from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from kavenegar import APIException, HTTPException, KavenegarAPI
from medogram.settings import BITPAY_API_KEY
from .models import APKDownloadStat, Comment, Blog, Order, Transaction, Visit, BoxMoney
from .serializers import (CustomUserProfileSerializer, BlogSerializer, BoxMoneySerializer, VisitSerializer,
                          CommentSerializer, CustomUserProfileJustUserNameSerializer)
from telemedicine.signals import apk_downloaded


User = get_user_model()

logger = logging.getLogger(__name__)


class RegisterOrLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Send a one-time authentication code to the provided phone number and create the user if missing.
        
        Expects 'phone_number' in request.data. Creates or retrieves a User with that phone number, generates a random 6-digit auth_code, saves it to the user, and attempts to send the code via Kavenegar's verify_lookup (using the 'users' template). Side effects: may create a new User and will update the user's auth_code.
        
        Returns:
        - 200 OK with a success message (Persian) when the SMS was sent.
        - 400 Bad Request if 'phone_number' is missing.
        - 500 Internal Server Error if sending the SMS fails.
        """
        phone_number = request.data.get('phone_number')

        if not phone_number:
            return Response(
                {'error': 'Phone number is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user, created = User.objects.get_or_create(phone_number=phone_number)

        # Generate a random 6-digit authentication code
        code = random.randint(100000, 999999)
        user.auth_code = code
        user.save(update_fields=['auth_code'])

        # Send SMS with the authentication code
        try:
            api = KavenegarAPI(settings.KAVEH_NEGAR_API_KEY)
            params = {
                'receptor': user.phone_number,
                'token': user.auth_code,
                'template': 'users'  # Ensure this template exists in Kaveh Negar
            }
            api.verify_lookup(params)
        except (APIException, HTTPException) as e:
            logger.error(f"Failed to send SMS to {user.phone_number}: {e}")
            return Response(
                {'error': 'Failed to send authentication code. Please try again later.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {'message': 'کد احراز هویت به شماره موبایل شما ارسال شد.'},
            status=status.HTTP_200_OK
        )


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Verify a one-time password (OTP) for a user's phone number and return JWT tokens on success.
        
        Expects 'phone_number' and 'code' in request.data. If a User with the given phone number exists and the numeric code matches user.auth_code, issues JWT refresh and access tokens and returns them in a 200 response. If the code is incorrect, returns a 400 response with an error message; if no user is found, returns a 404 response.
        
        Side effects:
        - If the user has no Visit records, attempts to send a one-time welcome SMS via Kavenegar using the 'first-log' template. Failures from the SMS API are caught and logged and do not affect the HTTP response.
        """
        phone_number = request.data.get('phone_number')
        code = request.data.get('code')

        try:
            user = User.objects.get(phone_number=phone_number)
            if user.auth_code == int(code):
                refresh = RefreshToken.for_user(user)
                response = Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }, status=status.HTTP_200_OK)
                
                
                # ─── پیامک خوش‌آمد فقط اگر هیچ ویزیتی ندارد ───
                if not Visit.objects.filter(user=user).exists():
                    try:
                        api = KavenegarAPI(settings.KAVEH_NEGAR_API_KEY)
                        api.verify_lookup({
                            'receptor': user.phone_number,
                            'token'   : 300000,   # مبلغ یا مقدار دل‌خواه
                            'template': 'first-log',
                        })
                    except (APIException, HTTPException) as exc:
                        logger.warning(f"Welcome SMS failed for {user.phone_number}: {exc}")

                return response

            return Response({'message': 'کد وارد شده صحیح نیست.'},
                            status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({'message': 'کاربری با این شماره موبایل پیدا نشد.'},
                            status=status.HTTP_404_NOT_FOUND)


class CreateTransaction(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Create a BitPay payment gateway request and record a Transaction for the authenticated user.
        
        Expects request.data['amount'] to be provided. Sends a POST to the BitPay gateway with the API key and amount; if the gateway returns a positive numeric id, creates a Transaction linked to request.user (amount and card_num set to the gateway id) and returns HTTP 200 with {'payment_url': <url>}. If the gateway response is non-positive, returns HTTP 400 with {'error': <gateway_response>}.
        
        Side effects:
        - Creates a Transaction record when the gateway returns a positive id.
        
        Input:
        - request.data['amount']: monetary amount to charge.
        
        Returns:
        - HTTP 200: {'payment_url': <str>}
        - HTTP 400: {'error': <str>} (gateway error text)
        """
        payment_data = {
            'api': BITPAY_API_KEY,
            'amount': request.data['amount'],
            'redirect': 'https://medogram.ir/payment-redirect/',
        }
        response = requests.post('https://bitpay.ir/payment/gateway-send', data=payment_data)
        id_get = response.text
        if int(id_get) > 0:
            transaction = Transaction.objects.create(
                user=request.user,
                amount=request.data['amount'],
                card_num=id_get
            )
            payment_url = f"https://bitpay.ir/payment/gateway-{id_get}-get"
            return Response({'payment_url': payment_url}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Error from BitPay: ' + id_get}, status=status.HTTP_400_BAD_REQUEST)


class VerifyPaymentView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Verify a BitPay payment using provided identifiers and update the matching Transaction record.
        
        Expects 'trans_id' and 'id_get' in request.data. Calls BitPay's gateway-result-second endpoint with the API key and the provided identifiers and interprets the JSON response:
        - If response 'status' == 1: finds the Transaction with card_num == id_get, sets its status to 'successful', sets factor_id to trans_id, saves the Transaction, and returns HTTP 200 with a success message.
        - If response 'status' == 11: returns HTTP 200 indicating the transaction was already verified.
        - Otherwise: returns HTTP 400 indicating verification failed.
        
        Parameters:
            request: DRF Request containing 'trans_id' and 'id_get' in request.data.
        
        Returns:
            rest_framework.response.Response with HTTP 200 on success (or already-verified) or HTTP 400 on failure.
        """
        trans_id = request.data.get('trans_id')
        id_get = request.data.get('id_get')
        if not trans_id or not id_get:
            return Response({'error': 'trans_id or id_get missing'}, status=status.HTTP_400_BAD_REQUEST)

        verify_data = {
            'api': settings.BITPAY_API_KEY,
            'trans_id': trans_id,
            'id_get': id_get,
            'json': 1
        }
        response = requests.post('https://bitpay.ir/payment/gateway-result-second', data=verify_data)
        result = response.json()
        if result.get('status') == 1:
            transaction = Transaction.objects.get(card_num=id_get)
            transaction.status = 'successful'
            transaction.factor_id = trans_id
            transaction.save()
            return Response({'message': 'Payment verified successfully'}, status=status.HTTP_200_OK)
        elif result.get('status') == 11:
            return Response({'message': 'Transaction verified in the past'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Payment verification failed'}, status=status.HTTP_400_BAD_REQUEST)


class CreateVisit(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        # بررسی موجودی کیف پول
        """
        Create a Visit charged against the authenticated user's wallet.
        
        Checks the user's BoxMoney balance (cost = 398000), returns 400 if insufficient. If balance is sufficient, validates VisitSerializer with the request data, deducts the visit cost from the wallet, attempts to save the Visit, and returns a 201 response with the created visit id and serialized data on success. If saving the visit fails, the wallet deduction is reverted and a 400 response with error details is returned. If the serializer is invalid, returns a 400 response with serializer errors.
        
        Returns:
            rest_framework.response.Response: HTTP 201 on success; 400 for validation errors, insufficient funds, or save failure.
        """
        box_money = BoxMoney.objects.select_for_update().get(user=request.user)
        visit_cost = 398000
        if not box_money.has_sufficient_balance(visit_cost):
            # اگر موجودی کافی نیست، برگرداندن پاسخ خطا
            logger.error(f"User {request.user.id} has insufficient balance for visit cost: {visit_cost}")
            return Response(
                {'error': 'موجودی کیف پول شما برای این ویزیت کافی نیست.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ایجاد سریالایزر با داده‌های ارسالی
        serializer = VisitSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            # کم کردن هزینه از کیف پول
            box_money.amount -= visit_cost
            box_money.save()

            # ذخیره ویزیت
            try:
                visit = serializer.save()
                return Response({
                    'message': 'ویزیت با موفقیت ثبت شد.',
                    'visit_id': visit.id,
                    'visit_data': VisitSerializer(visit).data
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                # در صورت خطا، برگرداندن پول به کیف پول
                logger.error(f"Error saving visit for user {request.user.id}: {e} - Reverting box money update for {visit_cost}")
                box_money.amount += visit_cost
                box_money.save()
                return Response({
                    'error': 'خطا در ثبت ویزیت',
                    'details': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            print(serializer.error)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        """
        Retrieve the authenticated user's visits ordered newest-first.
        
        Returns a 200 OK Response containing a list of VisitSerializer-serialized visit objects for request.user, ordered by descending creation time. The serializer is given the current request in its context.
        """
        visits = Visit.objects.filter(user=request.user).order_by('-created_at')
        serializer = VisitSerializer(visits, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Return the authenticated user's profile.
        
        Serializes the current request.user with CustomUserProfileSerializer and returns the serialized data in a 200 OK Response.
        """
        serializer = CustomUserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Partially update the authenticated user's profile.
        
        Validates provided fields with CustomUserProfileSerializer (partial=True) and saves on success.
        Returns HTTP 201 with the serialized user on success or HTTP 400 with serializer errors on validation failure.
        """
        serializer = CustomUserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BlogListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        """
        Return a serialized list of all Blog objects.
        
        Retrieves every Blog from the database, serializes them with BlogSerializer (many=True),
        and returns a DRF Response containing the serialized list with HTTP 200 OK.
        
        Returns:
            rest_framework.response.Response: JSON array of serialized blogs with status 200.
        """
        blogs = Blog.objects.all()
        serializer = BlogSerializer(blogs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class BlogCommentsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, blog_id):
        """
        Create a comment on the specified blog.
        
        Validates incoming comment data, saves a new Comment linked to the Blog identified by blog_id and the requesting user, and returns the serialized comment on success.
        
        Parameters:
            blog_id (int): Primary key of the Blog to attach the comment to.
        
        Returns:
            Response: HTTP 201 with serialized comment on success, or HTTP 400 with serializer errors on validation failure.
        
        Raises:
            Http404: If no Blog exists with the provided blog_id.
        """
        blog = get_object_or_404(Blog, pk=blog_id)
        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(blog=blog, user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommentLikeDislikeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, comment_id, actions):
        """
        Increment or decrement a comment's like count and return the updated count.
        
        If `actions` == 'like', increments the comment's `likes` by 1. If `actions` == 'dislike', decrements `likes` by 1 but never below 0. Persists the change and returns an HTTP 200 response with a message and the current like count.
        
        Parameters:
            comment_id (int): Primary key of the Comment to modify.
            actions (str): 'like' or 'dislike' indicating the operation.
        
        Raises:
            Http404: If no Comment with the given `comment_id` exists.
        """
        comment = get_object_or_404(Comment, id=comment_id)
        if actions == 'like':
            comment.likes += 1
        elif actions == 'dislike':
            comment.likes = max(0, comment.likes - 1)
        comment.save()

        return Response({'message': f'{actions.capitalize()} added', 'likes': comment.likes}, status=status.HTTP_200_OK)

class ShowBoxMoneyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Return the authenticated user's wallet (BoxMoney) data.
        
        Serializes the BoxMoney tied to request.user and returns it as a 200 OK JSON response.
        """
        box_money = BoxMoney.objects.get(user=request.user)
        serializer = BoxMoneySerializer(box_money)
        return Response(serializer.data, status=status.HTTP_200_OK)



class DownloadAPKView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        # مسیر فایل APK نسبت به همین اپ
        """
        Serve the APK file for download, emit a download-count signal, and include a download-count header.
        
        Looks for the APK at path relative to this module: 'apps/app-release.apk'. If the file does not exist, returns a 404 Response with an error message. When the file exists, sends the `apk_downloaded` signal (used only to record/count the event), returns a FileResponse that forces download with the filename "helssa.apk", and sets "Cache-Control: no-store" to discourage client/proxy caching. If an APKDownloadStat with key "helssa_apk" exists, its total is added to the response header "X-Helssa-Downloads" (otherwise that header is "0").
        """
        current_directory = os.path.dirname(__file__)
        file_path = os.path.join(current_directory, 'apps', 'app-release.apk')

        if not os.path.exists(file_path):
            return Response({"error": "File not found"}, status=404)

        # ارسال سیگنال شمارش (بدون IP — فقط ثبت شمارش)
        apk_downloaded.send(sender=self.__class__)

        # پاسخ دانلود فایل
        response = FileResponse(open(file_path, 'rb'), as_attachment=True, filename='helssa.apk')

        # اختیاری: جلوگیری از cache سمت کلاینت/پراکسی تا شمارش واقعی بماند
        response["Cache-Control"] = "no-store"

        # اختیاری: عدد فعلی را در هدر برگردان (برای مانیتورینگ کلاینتی)
        try:
            stat = APKDownloadStat.objects.only("total").get(key="helssa_apk")
            response["X-Helssa-Downloads"] = str(stat.total)
        except APKDownloadStat.DoesNotExist:
            response["X-Helssa-Downloads"] = "0"

        return response
            
        
class CreateSuperVisit(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, cost):
        # بررسی موجودی کیف پول
        """
        Create a Visit and charge the authenticated user's BoxMoney.
        
        Validates incoming visit data with VisitSerializer, ensures the requesting user's BoxMoney has at least `cost`, deducts `cost` from the wallet before attempting to save the Visit, and restores the deducted amount if saving fails. Operates within a transactional context (the caller uses select_for_update on BoxMoney) to prevent concurrent balance races.
        
        Parameters:
            cost (int | float): Amount to charge from the user's BoxMoney (same currency/units used by BoxMoney.amount).
        
        Returns:
            rest_framework.response.Response:
                - 201 Created: {'message', 'visit_id', 'visit_data'} when the visit is created successfully.
                - 400 Bad Request: serializer errors when input validation fails.
                - 400 Bad Request: {'error': 'خطا در ثبت ویزیت', 'details': <str>} if saving the Visit raises an exception (the deducted amount is restored).
                - 400 Bad Request: {'error': 'موجودی کیف پول شما برای این ویزیت کافی نیست.'} if the wallet balance is insufficient.
        """
        box_money = BoxMoney.objects.select_for_update().get(user=request.user)

        if box_money.amount < cost:
            return Response(
                {'error': 'موجودی کیف پول شما برای این ویزیت کافی نیست.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ایجاد سریالایزر با داده‌های ارسالی
        serializer = VisitSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            # کم کردن هزینه از کیف پول
            box_money.amount -= cost
            box_money.save()

            # ذخیره ویزیت
            try:
                visit = serializer.save()
                return Response({
                    'message': 'ویزیت با موفقیت ثبت شد.',
                    'visit_id': visit.id,
                    'visit_data': VisitSerializer(visit).data
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                # در صورت خطا، برگرداندن پول به کیف پول
                box_money.amount += cost
                box_money.save()
                return Response({
                    'error': 'خطا در ثبت ویزیت',
                    'details': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
class UserProfileViewJustUserName(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Return the authenticated user's profile containing only the username.
        
        Returns:
            Response: HTTP 200 with serialized user data limited to the username field.
        """
        serializer = CustomUserProfileJustUserNameSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
class UserProfileUpdateViewJustUserName(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Partially updates the current user's username fields using CustomUserProfileJustUserNameSerializer.
        
        Expects request.data to contain the username fields handled by the serializer. On successful validation and save returns HTTP 201 with the serialized user data; on validation failure returns HTTP 400 with serializer errors.
        """
        serializer = CustomUserProfileJustUserNameSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)






def order_verification(request, national_code):
    """
    Render the order verification page for a given national code.
    
    Looks up an Order by national_code and renders 'telemedicine/verification_order.html'.
    If found, context contains {'order': order, 'not_found': False}; if not found, context contains
    {'not_found': True, 'national_code': national_code}.
    
    Returns:
        HttpResponse: Rendered verification page.
    """
    try:
        order = Order.objects.get(national_code=national_code)
        context = {'order': order, 'not_found': False}
    except Order.DoesNotExist:
        context = {'not_found': True, 'national_code': national_code}

    return render(request, 'telemedicine/verification_order.html', context)


class download_order_file(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, national_code):
        """
        Return the PDF invoice for the Order identified by national_code as a downloadable file.
        
        Looks up the Order by national_code (raises Http404 if not found) and returns a FileResponse streaming
        MEDIA_ROOT/pdf/order/order_<national_code>.pdf with attachment filename "order_<national_code>.pdf".
        
        Parameters:
            request: Django HttpRequest (unused).
            national_code (str): National code used to find the Order and build the PDF filename.
        
        Returns:
            FileResponse: Streaming response with the order PDF as an attachment.
        
        Raises:
            django.http.Http404: If no Order with the given national_code exists.
        """
        order = get_object_or_404(Order, national_code=national_code)
        if order:
            file_path = os.path.join(settings.MEDIA_ROOT, 'pdf', 'order', f'order_{national_code}.pdf')
            response = FileResponse(open(file_path, 'rb'), as_attachment=True, filename=f'order_{national_code}.pdf')
            return response
        else:
            return Response({"error": "Order not found"}, status=404)


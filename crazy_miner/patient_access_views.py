"""
Views برای دسترسی به اطلاعات بیماران
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
import logging

from .patient_access_models import PatientAccessRequest, PatientDataCache
from .soapify_client import soapify_client
from kavenegar import KavenegarAPI
from django.conf import settings

logger = logging.getLogger(__name__)


class RequestPatientAccessView(APIView):
    """درخواست دسترسی به اطلاعات بیمار و ارسال OTP"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        patient_phone = request.data.get('patient_phone')
        
        if not patient_phone:
            return Response(
                {'error': 'شماره موبایل بیمار الزامی است'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # بررسی درخواست‌های قبلی فعال
        existing_request = PatientAccessRequest.objects.filter(
            doctor=request.user,
            patient_phone=patient_phone,
            status='verified',
            access_expires_at__gt=timezone.now()
        ).first()
        
        if existing_request:
            return Response({
                'message': 'شما در حال حاضر به این بیمار دسترسی دارید',
                'access_token': existing_request.access_token,
                'expires_at': existing_request.access_expires_at
            })
        
        # ایجاد درخواست جدید
        access_request = PatientAccessRequest.objects.create(
            doctor=request.user,
            patient_phone=patient_phone
        )
        
        # تولید و ارسال کد OTP
        otp_code = access_request.generate_otp()
        
        # ارسال SMS
        try:
            self._send_otp_sms(patient_phone, otp_code)
            
            return Response({
                'request_id': access_request.id,
                'message': 'کد تایید به شماره بیمار ارسال شد',
                'patient_phone': patient_phone
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"خطا در ارسال SMS: {str(e)}")
            access_request.delete()
            return Response(
                {'error': 'خطا در ارسال کد تایید'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _send_otp_sms(self, phone_number, otp_code):
        """ارسال کد OTP از طریق SMS"""
        api_key = getattr(settings, 'KAVEH_NEGAR_API_KEY', None)
        if not api_key:
            logger.warning("KAVEH_NEGAR_API_KEY تنظیم نشده است")
            return
        
        api = KavenegarAPI(api_key)
        api.verify_lookup({
            'receptor': phone_number,
            'token': otp_code,
            'template': 'patient-access-otp',  # نیاز به تعریف در پنل کاوه‌نگار
        })


class VerifyPatientAccessView(APIView):
    """تایید کد OTP و دریافت دسترسی"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        request_id = request.data.get('request_id')
        otp_code = request.data.get('otp_code')
        
        if not request_id or not otp_code:
            return Response(
                {'error': 'شناسه درخواست و کد تایید الزامی است'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # یافتن درخواست
        access_request = get_object_or_404(
            PatientAccessRequest,
            id=request_id,
            doctor=request.user,
            status='pending'
        )
        
        # تایید کد OTP
        if access_request.verify_otp(otp_code):
            return Response({
                'success': True,
                'message': 'دسترسی با موفقیت تایید شد',
                'access_token': access_request.access_token,
                'expires_at': access_request.access_expires_at
            })
        else:
            attempts_left = 3 - access_request.otp_attempts
            return Response({
                'success': False,
                'error': 'کد تایید اشتباه است',
                'attempts_left': max(0, attempts_left),
                'status': access_request.status
            }, status=status.HTTP_400_BAD_REQUEST)


class GetPatientDataView(APIView):
    """دریافت اطلاعات بیمار با استفاده از access token"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        access_token = request.headers.get('X-Patient-Access-Token')
        
        if not access_token:
            return Response(
                {'error': 'توکن دسترسی الزامی است'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # یافتن درخواست معتبر
        access_request = PatientAccessRequest.objects.filter(
            access_token=access_token,
            doctor=request.user,
            status='verified'
        ).first()
        
        if not access_request or not access_request.is_access_valid():
            return Response(
                {'error': 'توکن دسترسی نامعتبر یا منقضی شده است'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # بررسی کش
        cached_data = PatientDataCache.objects.filter(
            access_request=access_request,
            expires_at__gt=timezone.now()
        ).first()
        
        if cached_data:
            return Response({
                'patient_phone': cached_data.patient_phone,
                'patient_name': cached_data.patient_name,
                'latest_summary': cached_data.latest_summary,
                'summary_date': cached_data.summary_date,
                'from_cache': True
            })
        
        # دریافت اطلاعات از SOAPify
        try:
            result = soapify_client.get_patient_data(access_request.patient_phone)
            
            if not result['success']:
                return Response(
                    {'error': result.get('error', 'خطا در دریافت اطلاعات')},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            patient_data = result['patient']
            
            # ذخیره در کش
            cache_entry = PatientDataCache.objects.create(
                access_request=access_request,
                patient_id=patient_data['user']['id'],
                patient_name=patient_data['user'].get('username', ''),
                patient_phone=access_request.patient_phone,
                latest_summary=patient_data.get('latest_summary', {}),
                summary_date=timezone.now(),
                expires_at=timezone.now() + timezone.timedelta(hours=1)
            )
            
            return Response({
                'patient_phone': access_request.patient_phone,
                'patient_name': patient_data['user'].get('username', ''),
                'latest_summary': patient_data.get('latest_summary'),
                'has_summary': patient_data.get('has_summary', False),
                'from_cache': False
            })
            
        except Exception as e:
            logger.error(f"خطا در دریافت اطلاعات بیمار: {str(e)}")
            return Response(
                {'error': 'خطای سیستمی در دریافت اطلاعات'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CreateSOAPifyPaymentView(APIView):
    """ایجاد پرداخت برای کاربران SOAPify"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        amount = request.data.get('amount')
        soapify_user_id = request.data.get('soapify_user_id')
        description = request.data.get('description', 'پرداخت برای SOAPify')
        
        if not amount or not soapify_user_id:
            return Response(
                {'error': 'مبلغ و شناسه کاربر SOAPify الزامی است'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # استفاده از همان gateway موجود
            from .payment_gateway import crazy_gateway
            from .telemedicin_models import CrazyMinerPayment, CrazyMinerPaymentLog
            
            # ایجاد تراکنش با is_soapify=True
            payment = CrazyMinerPayment.objects.create(
                user=request.user,  # پزشک که پرداخت را انجام می‌دهد
                amount=amount,
                description=description,
                payment_type='service_payment',
                is_soapify=True,
                soapify_user_id=soapify_user_id,
                status='pending',
                redirect_url=getattr(settings, 'PAYMENT_REDIRECT_URL', 'https://medogram.ir/payment-redirect/'),
            )
            
            # لاگ
            CrazyMinerPaymentLog.objects.create(
                payment=payment,
                log_type='request',
                message=f'درخواست پرداخت برای SOAPify - کاربر: {soapify_user_id} - مبلغ: {amount}',
                raw_data={
                    'amount': str(amount),
                    'soapify_user_id': soapify_user_id,
                    'doctor_id': str(request.user.id)
                }
            )
            
            # ارسال به درگاه
            gateway_result = crazy_gateway.create_payment_request(
                amount=amount,
                order_id=payment.id,
                redirect_url=payment.redirect_url
            )
            
            if gateway_result['success']:
                payment.gateway_transaction_id = gateway_result['payment_id']
                payment.status = 'processing'
                payment.save()
                
                return Response({
                    'transaction_id': payment.id,
                    'payment_url': gateway_result['payment_url'],
                    'amount': amount,
                    'soapify_user_id': soapify_user_id,
                    'status': payment.status
                }, status=status.HTTP_201_CREATED)
            else:
                payment.status = 'failed'
                payment.save()
                
                return Response(
                    {'error': 'خطا در ایجاد پرداخت'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.error(f"خطا در ایجاد پرداخت SOAPify: {str(e)}")
            return Response(
                {'error': 'خطای سیستمی'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
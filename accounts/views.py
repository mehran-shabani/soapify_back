"""
Views for accounts app with mobile authentication.
"""

import random
from datetime import datetime, timedelta
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone
from .models import User, PhoneVerification
from .serializers import (
    UserSerializer,
    PhoneLoginSerializer,
    VerifyCodeSerializer,
    LoginSerializer,
    RegisterSerializer,
    ResetPasswordSerializer
)


def generate_verification_code():
    """Generate a 6-digit verification code"""
    return str(random.randint(100000, 999999))


def send_sms(phone_number, code):
    """Send SMS with verification code (placeholder)"""
    # TODO: Integrate with SMS provider
    print(f"Sending SMS to {phone_number}: Your verification code is {code}")
    return True


@api_view(['POST'])
@permission_classes([AllowAny])
def send_verification_code(request):
    """
    Send 6-digit verification code to phone number.
    """
    serializer = PhoneLoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    phone_number = serializer.validated_data['phone_number']
    purpose = request.data.get('purpose', 'login')  # login, register, reset_password
    
    # Generate and save code
    code = generate_verification_code()
    PhoneVerification.objects.create(
        phone_number=phone_number,
        code=code,
        purpose=purpose
    )
    
    # Send SMS
    if send_sms(phone_number, code):
        return Response({
            'message': 'Verification code sent successfully',
            'phone_number': phone_number
        })
    else:
        return Response({
            'error': 'Failed to send SMS'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    Register new user with phone verification.
    No token required for registration.
    """
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    
    # Verify phone code
    verification = PhoneVerification.objects.filter(
        phone_number=data['phone_number'],
        code=data['code'],
        purpose='register',
        is_used=False
    ).order_by('-created_at').first()
    
    if not verification or not verification.is_valid():
        return Response({
            'error': 'Invalid or expired verification code'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if username already exists
    if User.objects.filter(username=data['username']).exists():
        return Response({
            'error': 'Username already exists'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if phone number already registered
    if User.objects.filter(phone_number=data['phone_number']).exists():
        return Response({
            'error': 'Phone number already registered'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Create user
    with transaction.atomic():
        user = User.objects.create_user(
            username=data['username'],
            password=data['password'],
            phone_number=data['phone_number'],
            email=data.get('email', ''),
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            role=data.get('role', 'doctor')
        )
        
        # Mark verification as used
        verification.is_used = True
        verification.save()
    
    return Response({
        'message': 'User registered successfully',
        'user': UserSerializer(user).data
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    Login with username and password.
    No token required for login.
    Returns JWT access and refresh tokens.
    """
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    username = serializer.validated_data['username']
    password = serializer.validated_data['password']
    
    # Authenticate user
    user = authenticate(username=username, password=password)
    if not user:
        return Response({
            'error': 'Invalid credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    # Generate tokens
    refresh = RefreshToken.for_user(user)
    
    return Response({
        'access_token': str(refresh.access_token),
        'refresh_token': str(refresh),
        'token_type': 'Bearer',
        'user': UserSerializer(user).data
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_with_phone(request):
    """
    Login with phone number and verification code.
    """
    serializer = VerifyCodeSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    phone_number = serializer.validated_data['phone_number']
    code = serializer.validated_data['code']
    
    # Verify code
    verification = PhoneVerification.objects.filter(
        phone_number=phone_number,
        code=code,
        purpose='login',
        is_used=False
    ).order_by('-created_at').first()
    
    if not verification or not verification.is_valid():
        return Response({
            'error': 'Invalid or expired verification code'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Find user
    user = User.objects.filter(phone_number=phone_number).first()
    if not user:
        return Response({
            'error': 'User not found with this phone number'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Mark verification as used
    with transaction.atomic():
        verification.is_used = True
        verification.save()
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
    
    return Response({
        'access_token': str(refresh.access_token),
        'refresh_token': str(refresh),
        'token_type': 'Bearer',
        'user': UserSerializer(user).data
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token(request):
    """
    Refresh access token using refresh token.
    Requires username and password for additional security.
    """
    refresh_token = request.data.get('refresh_token')
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not all([refresh_token, username, password]):
        return Response({
            'error': 'refresh_token, username and password are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Verify credentials
    user = authenticate(username=username, password=password)
    if not user:
        return Response({
            'error': 'Invalid credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        # Verify refresh token
        refresh = RefreshToken(refresh_token)
        
        # Check if token belongs to the authenticated user
        if refresh['user_id'] != user.id:
            return Response({
                'error': 'Token does not belong to this user'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Generate new access token
        return Response({
            'access_token': str(refresh.access_token),
            'token_type': 'Bearer'
        })
    except Exception as e:
        return Response({
            'error': 'Invalid refresh token'
        }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    """
    Reset password using phone verification.
    """
    serializer = ResetPasswordSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    phone_number = serializer.validated_data['phone_number']
    code = serializer.validated_data['code']
    new_password = serializer.validated_data['new_password']
    
    # Verify code
    verification = PhoneVerification.objects.filter(
        phone_number=phone_number,
        code=code,
        purpose='reset_password',
        is_used=False
    ).order_by('-created_at').first()
    
    if not verification or not verification.is_valid():
        return Response({
            'error': 'Invalid or expired verification code'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Find user
    user = User.objects.filter(phone_number=phone_number).first()
    if not user:
        return Response({
            'error': 'User not found with this phone number'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Update password
    with transaction.atomic():
        user.set_password(new_password)
        user.save()
        
        # Mark verification as used
        verification.is_used = True
        verification.save()
    
    return Response({
        'message': 'Password reset successfully'
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    """
    Get current authenticated user info.
    """
    return Response({
        'user': UserSerializer(request.user).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    Logout user by blacklisting the refresh token.
    """
    try:
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({'message': 'Logged out successfully'})
    except Exception:
        return Response({'message': 'Logged out successfully'})
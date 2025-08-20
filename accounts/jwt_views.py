"""
JWT authentication views
"""

import secrets
from datetime import datetime, timedelta
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import authenticate
from django.db import transaction
from .models import User, UserSession
from .serializers import UserSerializer
from .authentication import (
    generate_jwt_token,
    generate_refresh_token,
    verify_refresh_token
)


@api_view(['POST'])
@permission_classes([AllowAny])
def jwt_login(request):
    """
    JWT login endpoint that returns access and refresh tokens
    """
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response({
            'error': 'Username and password are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Authenticate user
    user = authenticate(username=username, password=password)
    if not user:
        return Response({
            'error': 'Invalid credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    # Create session
    with transaction.atomic():
        session_token = secrets.token_hex(32)
        session = UserSession.objects.create(
            user=user,
            session_token=session_token,
            expires_at=datetime.now() + timedelta(days=7)
        )
        
        # Generate tokens
        access_token = generate_jwt_token(user, session_token)
        refresh_token = generate_refresh_token(user)
    
    return Response({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'Bearer',
        'expires_in': 1800,  # 30 minutes
        'user': UserSerializer(user).data
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def jwt_refresh(request):
    """
    Refresh JWT access token using refresh token
    """
    refresh_token = request.data.get('refresh_token')
    
    if not refresh_token:
        return Response({
            'error': 'Refresh token is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Verify refresh token
    user = verify_refresh_token(refresh_token)
    if not user:
        return Response({
            'error': 'Invalid refresh token'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    # Get active session or create new one
    active_session = UserSession.objects.filter(
        user=user,
        is_active=True,
        expires_at__gt=datetime.now()
    ).first()
    
    if not active_session:
        # Create new session
        session_token = secrets.token_hex(32)
        active_session = UserSession.objects.create(
            user=user,
            session_token=session_token,
            expires_at=datetime.now() + timedelta(days=7)
        )
    
    # Generate new access token
    access_token = generate_jwt_token(user, active_session.session_token)
    
    return Response({
        'access_token': access_token,
        'token_type': 'Bearer',
        'expires_in': 1800  # 30 minutes
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def jwt_logout(request):
    """
    Logout by invalidating the current session
    """
    # Get session token from JWT
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        try:
            import jwt
            from django.conf import settings

            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=['HS256'],
                options={"verify_exp": False}
            )
            session_token = payload.get('jti')
            if session_token:
                UserSession.objects.filter(
                    session_token=session_token,
                    user=request.user
                ).update(is_active=False)
        except jwt.PyJWTError:
            # It's okay to ignore decoding errors during logout.
            # The token might be expired or invalid, but we can still proceed with logout.
            pass
    
    return Response({
        'message': 'Logged out successfully'
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    """
    Get current authenticated user info
    """
    return Response({
        'user': UserSerializer(request.user).data
    })

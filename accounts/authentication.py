"""
JWT Authentication classes for SOAPify
"""

import jwt
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import UserSession

User = get_user_model()


class JWTAuthentication(BaseAuthentication):
    """
    Custom JWT authentication with 30-minute expiry
    """
    
    def authenticate(self, request):
        # Get token from Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header.split(' ')[1]
        
        try:
            # Decode token
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=['HS256'],
                options={"verify_exp": True}
            )
            
            # Verify audience
            if payload.get('aud') != 'soapify':
                raise AuthenticationFailed('Invalid audience')
            
            # Get user
            user = User.objects.get(id=payload['sub'])
            
            # Check if session is still active
            session_token = payload.get('jti')
            if session_token:
                try:
                    session = UserSession.objects.get(
                        session_token=session_token,
                        user=user,
                        is_active=True
                    )
                    # Check if session hasn't expired
                    if session.expires_at < datetime.now():
                        session.is_active = False
                        session.save()
                        raise AuthenticationFailed('Session expired')
                except UserSession.DoesNotExist:
                    raise AuthenticationFailed('Invalid session')
            
            return (user, token)
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token expired')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid token')
        except User.DoesNotExist:
            raise AuthenticationFailed('User not found')


def generate_jwt_token(user, session_token=None):
    """
    Generate JWT token with 30-minute expiry
    
    Args:
        user: User instance
        session_token: Optional session token for tracking
        
    Returns:
        JWT token string
    """
    now = datetime.utcnow()
    expiry = now + timedelta(minutes=30)
    
    payload = {
        'sub': str(user.id),
        'username': user.username,
        'role': user.role,
        'jti': session_token or str(user.id),
        'aud': 'soapify',
        'iat': now,
        'exp': expiry
    }
    
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
    return token


def generate_refresh_token(user):
    """
    Generate a long-lived refresh token
    
    Args:
        user: User instance
        
    Returns:
        Refresh token string
    """
    now = datetime.utcnow()
    expiry = now + timedelta(days=7)  # 7 days
    
    payload = {
        'sub': str(user.id),
        'type': 'refresh',
        'aud': 'soapify',
        'iat': now,
        'exp': expiry
    }
    
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
    return token


def verify_refresh_token(token):
    """
    Verify and decode refresh token
    
    Args:
        token: Refresh token string
        
    Returns:
        User instance or None
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=['HS256'],
            options={"verify_exp": True}
        )
        
        # Verify it's a refresh token
        if payload.get('type') != 'refresh' or payload.get('aud') != 'soapify':
            return None
        
        # Get user
        user = User.objects.get(id=payload['sub'])
        return user
        
    except (jwt.InvalidTokenError, User.DoesNotExist):
        return None
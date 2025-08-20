"""
JWT window management service for 30-minute sessions.
"""

import jwt
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from django.conf import settings
from django.utils import timezone
from accounts.models import UserSession

logger = logging.getLogger(__name__)


class JWTWindowService:
    """Service for managing JWT windows with 30-minute expiration."""
    
    def __init__(self):
        self.secret_key = settings.LOCAL_JWT_SECRET or settings.SECRET_KEY
        self.algorithm = 'HS256'
        self.window_duration_minutes = 30
        self.max_concurrent_sessions = 3
    
    def create_jwt_window(self, user, session_data: Dict = None) -> Dict:
        """
        Create a new JWT window for user.
        
        Args:
            user: Django User instance
            session_data: Additional session data
            
        Returns:
            Dict with JWT token and session info
        """
        try:
            # Clean up expired sessions for this user
            self._cleanup_expired_sessions(user)
            
            # Check concurrent session limit
            active_sessions = UserSession.objects.filter(
                user=user,
                is_active=True,
                expires_at__gt=timezone.now()
            ).count()
            
            if active_sessions >= self.max_concurrent_sessions:
                # Deactivate oldest session
                oldest_session = UserSession.objects.filter(
                    user=user,
                    is_active=True
                ).order_by('created_at').first()
                
                if oldest_session:
                    oldest_session.is_active = False
                    oldest_session.save()
                    logger.info(f"Deactivated oldest session for user {user.username}")
            
            # Create new session
            expires_at = timezone.now() + timedelta(minutes=self.window_duration_minutes)
            
            # Prepare JWT payload
            payload = {
                'user_id': user.id,
                'username': user.username,
                'role': getattr(user, 'role', 'doctor'),
                'session_id': str(uuid.uuid4()),
                'iat': int(time.time()),
                'exp': int(expires_at.timestamp()),
                'window_duration': self.window_duration_minutes
            }
            
            # Add custom session data
            if session_data:
                payload.update(session_data)
            
            # Generate JWT token
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            
            # Create UserSession record
            user_session = UserSession.objects.create(
                user=user,
                session_token=token,
                expires_at=expires_at,
                is_active=True
            )
            
            logger.info(f"Created JWT window for user {user.username}, expires at {expires_at}")
            
            return {
                'success': True,
                'token': token,
                'session_id': user_session.id,
                'expires_at': expires_at.isoformat(),
                'window_duration_minutes': self.window_duration_minutes,
                'remaining_time_minutes': self.window_duration_minutes
            }
            
        except Exception as e:
            logger.error(f"Failed to create JWT window for user {user.username}: {e}")
            return {
                'success': False,
                'error': f'Failed to create session: {str(e)}'
            }
    
    def validate_jwt_window(self, token: str) -> Dict:
        """
        Validate JWT token and check window status.
        
        Args:
            token: JWT token to validate
            
        Returns:
            Dict with validation result and session info
        """
        try:
            # Decode JWT token
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            # Check if session exists and is active
            try:
                user_session = UserSession.objects.get(
                    session_token=token,
                    is_active=True
                )
            except UserSession.DoesNotExist:
                logger.warning(f"Session not found or inactive for token")
                return {
                    'valid': False,
                    'error': 'Session not found or inactive'
                }
            
            # Check expiration
            if timezone.now() > user_session.expires_at:
                user_session.is_active = False
                user_session.save()
                logger.info(f"Session expired for user {payload.get('username')}")
                return {
                    'valid': False,
                    'expired': True,
                    'error': 'Session expired'
                }
            
            # Calculate remaining time
            remaining_time = user_session.expires_at - timezone.now()
            remaining_minutes = int(remaining_time.total_seconds() / 60)
            
            logger.debug(f"JWT window valid for user {payload.get('username')}, {remaining_minutes}m remaining")
            
            return {
                'valid': True,
                'payload': payload,
                'session_id': user_session.id,
                'expires_at': user_session.expires_at.isoformat(),
                'remaining_time_minutes': remaining_minutes,
                'user_id': payload.get('user_id'),
                'username': payload.get('username'),
                'role': payload.get('role')
            }
            
        except jwt.ExpiredSignatureError:
            logger.info("JWT token expired")
            return {
                'valid': False,
                'expired': True,
                'error': 'Token expired'
            }
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return {
                'valid': False,
                'error': f'Invalid token: {str(e)}'
            }
        except Exception as e:
            logger.error(f"JWT validation failed: {e}")
            return {
                'valid': False,
                'error': f'Validation failed: {str(e)}'
            }
    
    def extend_jwt_window(self, token: str, additional_minutes: int = 30) -> Dict:
        """
        Extend JWT window duration.
        
        Args:
            token: Current JWT token
            additional_minutes: Minutes to add to current expiration
            
        Returns:
            Dict with extension result
        """
        try:
            # Validate current token
            validation_result = self.validate_jwt_window(token)
            if not validation_result.get('valid'):
                return validation_result
            
            # Get user session
            user_session = UserSession.objects.get(
                session_token=token,
                is_active=True
            )
            
            # Extend expiration
            new_expires_at = user_session.expires_at + timedelta(minutes=additional_minutes)
            user_session.expires_at = new_expires_at
            user_session.save()
            
            # Update JWT payload
            payload = validation_result['payload']
            payload['exp'] = int(new_expires_at.timestamp())
            
            # Generate new token
            new_token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            
            # Update session token
            user_session.session_token = new_token
            user_session.save()
            
            remaining_time = new_expires_at - timezone.now()
            remaining_minutes = int(remaining_time.total_seconds() / 60)
            
            logger.info(f"Extended JWT window for user {payload.get('username')} by {additional_minutes}m")
            
            return {
                'success': True,
                'token': new_token,
                'expires_at': new_expires_at.isoformat(),
                'remaining_time_minutes': remaining_minutes,
                'extended_by_minutes': additional_minutes
            }
            
        except Exception as e:
            logger.error(f"Failed to extend JWT window: {e}")
            return {
                'success': False,
                'error': f'Extension failed: {str(e)}'
            }
    
    def revoke_jwt_window(self, token: str) -> Dict:
        """
        Revoke JWT window (logout).
        
        Args:
            token: JWT token to revoke
            
        Returns:
            Dict with revocation result
        """
        try:
            # Find and deactivate session
            user_session = UserSession.objects.get(
                session_token=token,
                is_active=True
            )
            
            user_session.is_active = False
            user_session.save()
            
            logger.info(f"Revoked JWT window for user {user_session.user.username}")
            
            return {
                'success': True,
                'message': 'Session revoked successfully'
            }
            
        except UserSession.DoesNotExist:
            return {
                'success': True,
                'message': 'Session already inactive'
            }
        except Exception as e:
            logger.error(f"Failed to revoke JWT window: {e}")
            return {
                'success': False,
                'error': f'Revocation failed: {str(e)}'
            }
    
    def _cleanup_expired_sessions(self, user):
        """Clean up expired sessions for user."""
        try:
            expired_count = UserSession.objects.filter(
                user=user,
                expires_at__lt=timezone.now()
            ).update(is_active=False)
            
            if expired_count > 0:
                logger.debug(f"Cleaned up {expired_count} expired sessions for user {user.username}")
                
        except Exception as e:
            logger.warning(f"Failed to cleanup expired sessions: {e}")


import uuid  # Add missing import

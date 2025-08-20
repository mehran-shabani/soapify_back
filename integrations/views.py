"""
Views for external integrations and authentication.
"""

import time
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from .models import OTPSession, PatientAccessSession, ExternalServiceLog, IntegrationHealth
from .clients.crazy_miner_client import CrazyMinerClient
from .clients.helssa_client import HelssaClient
from .services.jwt_window_service import JWTWindowService
from .serializers import OTPSessionSerializer, PatientAccessSessionSerializer
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def send_otp(request):
    """
    Send OTP for authentication.
    """
    start_time = time.time()
    
    try:
        phone_number = request.data.get('phone_number', '').strip()
        
        if not phone_number:
            return Response(
                {'error': 'Phone number is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate phone number format (basic validation)
        if not phone_number.startswith('+98') or len(phone_number) != 13:
            return Response(
                {'error': 'Invalid phone number format. Use +98XXXXXXXXX'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check for recent OTP requests (rate limiting)
        recent_otp = OTPSession.objects.filter(
            phone_number=phone_number,
            created_at__gte=timezone.now() - timezone.timedelta(minutes=2)
        ).first()
        
        if recent_otp and recent_otp.status == 'pending':
            return Response(
                {'error': 'OTP already sent recently. Please wait before requesting again.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        # Create OTP session
        otp_session = OTPSession.objects.create(
            phone_number=phone_number,
            expires_at=timezone.now() + timezone.timedelta(minutes=5),
            send_attempts=1
        )
        
        # Send OTP via Crazy Miner
        crazy_miner = CrazyMinerClient()
        otp_result = crazy_miner.send_otp(
            phone_number,
            f"کد تأیید SOAPify: {{otp_code}}\nاین کد تا 5 دقیقه معتبر است."
        )
        
        # Log the API call
        ExternalServiceLog.objects.create(
            service='crazy_miner',
            action='otp_send',
            endpoint='/api/v1/otp/send',
            request_data={'phone_number': phone_number},
            success=otp_result.get('success', False),
            error_message=otp_result.get('error', ''),
            response_time_ms=int((time.time() - start_time) * 1000)
        )
        
        if otp_result.get('success'):
            # Update OTP session
            otp_session.status = 'sent'
            otp_session.sent_at = timezone.now()
            otp_session.otp_id = otp_result.get('otp_id', '')
            otp_session.save()
            
            return Response({
                'message': 'OTP sent successfully',
                'session_id': otp_session.id,
                'expires_at': otp_session.expires_at.isoformat(),
                'phone_number': phone_number
            })
        else:
            # Update OTP session with error
            otp_session.status = 'failed'
            otp_session.last_error = otp_result.get('error', 'Unknown error')
            otp_session.save()
            
            return Response(
                {'error': f"Failed to send OTP: {otp_result.get('error')}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    except Exception as e:
        logger.error(f"OTP sending failed: {e}")
        return Response(
            {'error': f'OTP sending failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp(request):
    """
    Verify OTP and create JWT window.
    """
    start_time = time.time()
    
    try:
        phone_number = request.data.get('phone_number', '').strip()
        otp_code = request.data.get('otp_code', '').strip()
        session_id = request.data.get('session_id')
        
        if not all([phone_number, otp_code]):
            return Response(
                {'error': 'Phone number and OTP code are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get OTP session
        try:
            if session_id:
                otp_session = OTPSession.objects.get(id=session_id, phone_number=phone_number)
            else:
                otp_session = OTPSession.objects.filter(
                    phone_number=phone_number,
                    status='sent'
                ).order_by('-created_at').first()
                
                if not otp_session:
                    return Response(
                        {'error': 'No valid OTP session found'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
        except OTPSession.DoesNotExist:
            return Response(
                {'error': 'OTP session not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if OTP can be verified
        if not otp_session.can_verify:
            if otp_session.is_expired:
                error_msg = 'OTP has expired'
            else:
                error_msg = 'Maximum verification attempts exceeded'
            
            return Response(
                {'error': error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify OTP via Crazy Miner
        crazy_miner = CrazyMinerClient()
        verify_result = crazy_miner.verify_otp(
            phone_number,
            otp_code,
            otp_session.otp_id
        )
        
        # Log the API call
        ExternalServiceLog.objects.create(
            service='crazy_miner',
            action='otp_verify',
            endpoint='/api/v1/otp/verify',
            request_data={'phone_number': phone_number},
            success=verify_result.get('verified', False),
            error_message=verify_result.get('error', ''),
            response_time_ms=int((time.time() - start_time) * 1000)
        )
        
        # Update OTP session
        otp_session.increment_verify_attempt()
        
        if verify_result.get('verified'):
            # OTP verified successfully
            otp_session.status = 'verified'
            otp_session.verified_at = timezone.now()
            
            # Find or create user (in a real system, this would be more sophisticated)
            user, created = User.objects.get_or_create(
                username=phone_number,
                defaults={
                    'phone_number': phone_number,
                    'is_active': True
                }
            )
            
            otp_session.verified_user = user
            otp_session.save()
            
            # Create JWT window
            jwt_service = JWTWindowService()
            jwt_result = jwt_service.create_jwt_window(
                user,
                {
                    'phone_number': phone_number,
                    'otp_session_id': otp_session.id,
                    'auth_method': 'otp'
                }
            )
            
            if jwt_result.get('success'):
                logger.info(f"OTP verified and JWT window created for {phone_number}")
                
                return Response({
                    'message': 'OTP verified successfully',
                    'verified': True,
                    'jwt_token': jwt_result['token'],
                    'session_id': jwt_result['session_id'],
                    'expires_at': jwt_result['expires_at'],
                    'window_duration_minutes': jwt_result['window_duration_minutes'],
                    'user_id': user.id,
                    'username': user.username
                })
            else:
                return Response(
                    {'error': f"JWT creation failed: {jwt_result.get('error')}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            # OTP verification failed
            otp_session.last_error = verify_result.get('error', 'Invalid OTP')
            otp_session.save()
            
            return Response(
                {'error': verify_result.get('error', 'Invalid OTP code')},
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except Exception as e:
        logger.error(f"OTP verification failed: {e}")
        return Response(
            {'error': f'Verification failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_patients(request):
    """
    Search patients via Helssa (read-only).
    """
    start_time = time.time()
    
    try:
        query = request.GET.get('q', '').strip()
        limit = int(request.GET.get('limit', 20))
        
        if not query or len(query) < 2:
            return Response(
                {'error': 'Search query must be at least 2 characters'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Search patients via Helssa
        helssa = HelssaClient()
        search_result = helssa.search_patients(query, limit)
        
        # Log the API call
        ExternalServiceLog.objects.create(
            service='helssa',
            action='patient_search',
            endpoint='/api/v1/patients/search',
            request_data={'query': query, 'limit': limit},
            user=request.user,
            success=search_result.get('success', False),
            error_message=search_result.get('error', ''),
            response_time_ms=int((time.time() - start_time) * 1000)
        )
        
        if search_result.get('success'):
            return Response({
                'patients': search_result.get('patients', []),
                'total_results': search_result.get('total_results', 0),
                'query': query
            })
        else:
            return Response(
                {'error': search_result.get('error', 'Search failed')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    except Exception as e:
        logger.error(f"Patient search failed: {e}")
        return Response(
            {'error': f'Search failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_patient_access(request, patient_ref):
    """
    Request access to patient data via Helssa.
    """
    start_time = time.time()
    
    try:
        # Check if access already exists and is valid
        existing_access = PatientAccessSession.objects.filter(
            user=request.user,
            patient_ref=patient_ref,
            access_granted=True,
            expires_at__gt=timezone.now()
        ).first()
        
        if existing_access:
            return Response({
                'message': 'Access already granted',
                'access_granted': True,
                'expires_at': existing_access.expires_at.isoformat(),
                'access_level': existing_access.access_level
            })
        
        # Request access via Helssa
        helssa = HelssaClient()
        access_result = helssa.verify_patient_access(patient_ref, request.user.username)
        
        # Log the API call
        ExternalServiceLog.objects.create(
            service='helssa',
            action='access_verify',
            endpoint='/api/v1/access/verify',
            request_data={'patient_ref': patient_ref, 'doctor_id': request.user.username},
            user=request.user,
            success=access_result.get('access_granted', False),
            error_message=access_result.get('error', ''),
            response_time_ms=int((time.time() - start_time) * 1000)
        )
        
        # Create or update access session
        access_session, created = PatientAccessSession.objects.update_or_create(
            user=request.user,
            patient_ref=patient_ref,
            defaults={
                'access_granted': access_result.get('access_granted', False),
                'access_level': access_result.get('access_level', 'read_only'),
                'granted_at': timezone.now() if access_result.get('access_granted') else None,
                'expires_at': timezone.now() + timezone.timedelta(hours=8) if access_result.get('access_granted') else None
            }
        )
        
        if access_result.get('access_granted'):
            return Response({
                'message': 'Patient access granted',
                'access_granted': True,
                'patient_ref': patient_ref,
                'access_level': access_session.access_level,
                'expires_at': access_session.expires_at.isoformat()
            })
        else:
            return Response(
                {'error': access_result.get('error', 'Access denied')},
                status=status.HTTP_403_FORBIDDEN
            )
            
    except Exception as e:
        logger.error(f"Patient access request failed for {patient_ref}: {e}")
        return Response(
            {'error': f'Access request failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_patient_info(request, patient_ref):
    """
    Get basic patient information (no PHI).
    """
    start_time = time.time()
    
    try:
        # Check if user has access to this patient
        access_session = PatientAccessSession.objects.filter(
            user=request.user,
            patient_ref=patient_ref,
            access_granted=True,
            expires_at__gt=timezone.now()
        ).first()
        
        if not access_session:
            return Response(
                {'error': 'No active access to this patient. Request access first.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get patient info via Helssa
        helssa = HelssaClient()
        patient_result = helssa.get_patient_basic_info(patient_ref)
        
        # Log the API call
        ExternalServiceLog.objects.create(
            service='helssa',
            action='patient_info',
            endpoint=f'/api/v1/patients/{patient_ref}/basic',
            request_data={'patient_ref': patient_ref},
            user=request.user,
            success=patient_result.get('success', False),
            error_message=patient_result.get('error', ''),
            response_time_ms=int((time.time() - start_time) * 1000)
        )
        
        # Record access
        access_session.record_access()
        
        if patient_result.get('success'):
            return Response({
                'patient': patient_result.get('patient', {}),
                'access_info': {
                    'access_level': access_session.access_level,
                    'expires_at': access_session.expires_at.isoformat(),
                    'access_count': access_session.access_count
                }
            })
        else:
            return Response(
                {'error': patient_result.get('error', 'Failed to get patient info')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    except Exception as e:
        logger.error(f"Failed to get patient info for {patient_ref}: {e}")
        return Response(
            {'error': f'Failed to get patient info: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def extend_session(request):
    """
    Extend current JWT window.
    """
    try:
        additional_minutes = request.data.get('additional_minutes', 30)
        
        if additional_minutes < 1 or additional_minutes > 60:
            return Response(
                {'error': 'Additional minutes must be between 1 and 60'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get current JWT token from Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return Response(
                {'error': 'JWT token required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        token = auth_header.split(' ')[1]
        
        # Extend JWT window
        jwt_service = JWTWindowService()
        extend_result = jwt_service.extend_jwt_window(token, additional_minutes)
        
        if extend_result.get('success'):
            return Response({
                'message': 'Session extended successfully',
                'new_token': extend_result['token'],
                'expires_at': extend_result['expires_at'],
                'remaining_time_minutes': extend_result['remaining_time_minutes'],
                'extended_by_minutes': extend_result['extended_by_minutes']
            })
        else:
            return Response(
                {'error': extend_result.get('error', 'Extension failed')},
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except Exception as e:
        logger.error(f"Session extension failed: {e}")
        return Response(
            {'error': f'Extension failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    Logout and revoke JWT window.
    """
    try:
        # Get current JWT token
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            
            # Revoke JWT window
            jwt_service = JWTWindowService()
            revoke_result = jwt_service.revoke_jwt_window(token)
            
            logger.info(f"User {request.user.username} logged out")
            
            return Response({
                'message': 'Logged out successfully'
            })
        else:
            return Response({
                'message': 'No active session to logout'
            })
            
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        return Response(
            {'error': f'Logout failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_session_status(request):
    """
    Get current session status and remaining time.
    """
    try:
        # Get current JWT token
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return Response(
                {'error': 'JWT token required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        token = auth_header.split(' ')[1]
        
        # Validate JWT window
        jwt_service = JWTWindowService()
        validation_result = jwt_service.validate_jwt_window(token)
        
        if validation_result.get('valid'):
            return Response({
                'valid': True,
                'user_id': validation_result['user_id'],
                'username': validation_result['username'],
                'role': validation_result['role'],
                'expires_at': validation_result['expires_at'],
                'remaining_time_minutes': validation_result['remaining_time_minutes']
            })
        else:
            return Response({
                'valid': False,
                'error': validation_result.get('error', 'Invalid session')
            })
            
    except Exception as e:
        logger.error(f"Session status check failed: {e}")
        return Response(
            {'error': f'Status check failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def integration_health(request):
    """
    Get health status of all external integrations.
    """
    try:
        health_records = IntegrationHealth.objects.all()
        
        health_status = {}
        for record in health_records:
            health_status[record.service] = {
                'healthy': record.is_healthy,
                'last_check': record.last_check_at.isoformat(),
                'last_success': record.last_success_at.isoformat() if record.last_success_at else None,
                'response_time_ms': record.response_time_ms,
                'consecutive_failures': record.consecutive_failures,
                'last_error': record.last_error
            }
        
        return Response({
            'overall_status': all(record.is_healthy for record in health_records),
            'services': health_status
        })
        
    except Exception as e:
        logger.error(f"Integration health check failed: {e}")
        return Response(
            {'error': f'Health check failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

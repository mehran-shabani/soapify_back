import hmac
import hashlib
import time
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.conf import settings
from django.core.cache import cache


class HMACMiddleware(MiddlewareMixin):
    """
    HMAC authentication for inter-service communication
    """
    
    # Paths that require HMAC authentication
    HMAC_REQUIRED_PATHS = [
        '/internal/',
        '/service-to-service/',
    ]
    
    def process_request(self, request):
        # Check if path requires HMAC
        requires_hmac = any(
            request.path.startswith(path) 
            for path in self.HMAC_REQUIRED_PATHS
        )
        
        if not requires_hmac:
            return None
        
        # Get HMAC headers
        signature = request.META.get('HTTP_X_HMAC_SIGNATURE')
        timestamp = request.META.get('HTTP_X_TIMESTAMP')
        nonce = request.META.get('HTTP_X_NONCE')
        
        if not all([signature, timestamp, nonce]):
            return JsonResponse({
                'error': 'Missing authentication headers'
            }, status=401)
        
        # Check timestamp (5 minute window)
        try:
            req_timestamp = float(timestamp)
            if abs(time.time() - req_timestamp) > 300:
                return JsonResponse({
                    'error': 'Request timestamp too old'
                }, status=401)
        except (ValueError, TypeError):
            return JsonResponse({
                'error': 'Invalid timestamp'
            }, status=401)
        
        # Check nonce for replay protection
        nonce_key = f'hmac_nonce:{nonce}'
        if cache.get(nonce_key):
            return JsonResponse({
                'error': 'Nonce already used'
            }, status=401)
        
        # Verify HMAC signature
        secret = getattr(settings, 'HMAC_SECRET_KEY', settings.SECRET_KEY)
        
        # Build message to sign
        message = f"{request.method}:{request.path}:{timestamp}:{nonce}"
        if request.body:
            message += f":{request.body.decode('utf-8')}"
        
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            return JsonResponse({
                'error': 'Invalid signature'
            }, status=401)
        
        # Store nonce to prevent replay
        cache.set(nonce_key, True, 300)  # 5 minutes
        
        return None
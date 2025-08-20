"""
HMAC authentication middleware for secure API communications.
"""

import hmac
import hashlib
import time
import re
from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger(__name__)


class HMACAuthenticationMiddleware(MiddlewareMixin):
    """
    Middleware for HMAC authentication on sensitive endpoints.
    """
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.hmac_secret = settings.HMAC_SHARED_SECRET
        self.enforce_paths = getattr(settings, 'HMAC_ENFORCE_PATHS', [])
        self.nonce_cache = {}  # In production, use Redis
        self.max_timestamp_skew = 300  # 5 minutes
        
        # Compile regex patterns for path matching
        self.path_patterns = []
        for path_pattern in self.enforce_paths:
            try:
                self.path_patterns.append(re.compile(path_pattern))
            except re.error as e:
                logger.warning(f"Invalid HMAC path pattern {path_pattern}: {e}")
    
    def process_request(self, request):
        """Process incoming request for HMAC authentication."""
        
        # Skip if HMAC not configured
        if not self.hmac_secret:
            return None
        
        # Check if path requires HMAC authentication
        if not self._should_enforce_hmac(request.path):
            return None
        
        # Extract HMAC headers
        signature = request.META.get('HTTP_X_HMAC_SIGNATURE')
        timestamp = request.META.get('HTTP_X_HMAC_TIMESTAMP')
        nonce = request.META.get('HTTP_X_HMAC_NONCE')
        
        if not all([signature, timestamp, nonce]):
            logger.warning(f"Missing HMAC headers for {request.path}")
            return JsonResponse({
                'error': 'Missing HMAC authentication headers',
                'required_headers': ['X-HMAC-Signature', 'X-HMAC-Timestamp', 'X-HMAC-Nonce']
            }, status=401)
        
        # Validate timestamp
        try:
            request_timestamp = float(timestamp)
            current_timestamp = time.time()
            
            if abs(current_timestamp - request_timestamp) > self.max_timestamp_skew:
                logger.warning(f"HMAC timestamp skew too large for {request.path}")
                return JsonResponse({
                    'error': 'Request timestamp outside acceptable window',
                    'max_skew_seconds': self.max_timestamp_skew
                }, status=401)
        except (ValueError, TypeError):
            logger.warning(f"Invalid HMAC timestamp for {request.path}")
            return JsonResponse({'error': 'Invalid timestamp format'}, status=401)
        
        # Check nonce for replay protection
        if self._is_nonce_used(nonce, request_timestamp):
            logger.warning(f"Replay attack detected for {request.path}, nonce: {nonce}")
            return JsonResponse({'error': 'Nonce already used (replay attack detected)'}, status=401)
        
        # Validate HMAC signature
        if not self._validate_hmac_signature(request, signature, timestamp, nonce):
            logger.warning(f"Invalid HMAC signature for {request.path}")
            return JsonResponse({'error': 'Invalid HMAC signature'}, status=401)
        
        # Store nonce to prevent replay
        self._store_nonce(nonce, request_timestamp)
        
        logger.info(f"HMAC authentication successful for {request.path}")
        return None
    
    def _should_enforce_hmac(self, path: str) -> bool:
        """Check if path requires HMAC authentication."""
        for pattern in self.path_patterns:
            if pattern.match(path):
                return True
        return False
    
    def _validate_hmac_signature(self, request, signature: str, timestamp: str, nonce: str) -> bool:
        """Validate HMAC signature."""
        try:
            # Get request body
            body = request.body.decode('utf-8') if request.body else ''
            
            # Create message to sign
            message_parts = [
                request.method,
                request.path,
                timestamp,
                nonce,
                body
            ]
            message = '\n'.join(message_parts)
            
            # Calculate expected signature
            expected_signature = hmac.new(
                self.hmac_secret.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures (constant time comparison)
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error(f"HMAC signature validation error: {e}")
            return False
    
    def _is_nonce_used(self, nonce: str, timestamp: float) -> bool:
        """Check if nonce has been used recently."""
        # Clean old nonces (older than max_timestamp_skew)
        cutoff_time = timestamp - self.max_timestamp_skew
        self.nonce_cache = {
            n: t for n, t in self.nonce_cache.items() 
            if t > cutoff_time
        }
        
        return nonce in self.nonce_cache
    
    def _store_nonce(self, nonce: str, timestamp: float):
        """Store nonce to prevent replay attacks."""
        self.nonce_cache[nonce] = timestamp
        
        # Limit cache size (in production, use Redis with TTL)
        if len(self.nonce_cache) > 10000:
            # Remove oldest entries
            sorted_nonces = sorted(self.nonce_cache.items(), key=lambda x: x[1])
            for old_nonce, _ in sorted_nonces[:1000]:
                del self.nonce_cache[old_nonce]


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware for adding security headers.
    """
    
    def process_response(self, request, response):
        """Add security headers to response."""
        
        # Content Security Policy
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "connect-src 'self';"
        )
        
        # Other security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'microphone=(), camera=(), geolocation=()'
        
        # HSTS (only in production)
        if not settings.DEBUG:
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response

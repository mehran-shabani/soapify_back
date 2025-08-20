import time
from collections import defaultdict
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.core.cache import cache
from django.conf import settings


class RateLimitMiddleware(MiddlewareMixin):
    """
    Rate limiting middleware to prevent abuse
    """
    
    # Default rate limits (requests per minute)
    RATE_LIMITS = {
        '/auth/login': 5,
        '/auth/refresh': 10,
        '/auth/register': 3,
        '/encounters/': 30,
        '/encounters/chunks/presign': 60,
    }
    
    def process_request(self, request):
        # Skip rate limiting in debug mode
        if settings.DEBUG:
            return None
            
        # Get client IP
        ip = self.get_client_ip(request)
        
        # Check if path needs rate limiting
        for path, limit in self.RATE_LIMITS.items():
            if request.path.startswith(path):
                cache_key = f'rate_limit:{ip}:{path}'
                
                # Get current count
                current = cache.get(cache_key, 0)
                
                if current >= limit:
                    return JsonResponse({
                        'error': 'Rate limit exceeded',
                        'message': f'Too many requests. Please try again later.',
                        'retry_after': 60
                    }, status=429)
                
                # Increment counter
                cache.set(cache_key, current + 1, 60)  # 60 seconds window
                
                break
        
        return None
    
    def get_client_ip(self, request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
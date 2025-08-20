import hashlib
import secrets
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse
from django.conf import settings


class SecurityMiddleware(MiddlewareMixin):
    """
    Security middleware to add security headers and protections
    """
    
    def process_request(self, request):
        # Add request ID for tracing
        if not hasattr(request, 'request_id'):
            request.request_id = secrets.token_hex(16)
        
        return None
    
    def process_response(self, request, response):
        # Security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # CSP header
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://api.gapgpt.app https://api.gapapi.com"
        )
        response['Content-Security-Policy'] = csp
        
        # HSTS header for production
        if not settings.DEBUG:
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Add request ID to response
        if hasattr(request, 'request_id'):
            response['X-Request-ID'] = request.request_id
        
        return response
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse
from django.conf import settings


class CORSMiddleware(MiddlewareMixin):
    """
    Enhanced CORS middleware with proper security
    """
    
    def process_request(self, request):
        # Handle preflight requests
        if request.method == 'OPTIONS':
            response = HttpResponse()
            self.add_cors_headers(request, response)
            return response
        return None
    
    def process_response(self, request, response):
        self.add_cors_headers(request, response)
        return response
    
    def add_cors_headers(self, request, response):
        # Get allowed origins from settings
        allowed_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [
            'http://localhost:3000',
            'http://127.0.0.1:3000',
        ])
        
        origin = request.META.get('HTTP_ORIGIN')
        
        # Check if origin is allowed
        if origin in allowed_origins or settings.DEBUG:
            response['Access-Control-Allow-Origin'] = origin or '*'
            response['Access-Control-Allow-Credentials'] = 'true'
        
        # Set allowed methods and headers
        response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
        response['Access-Control-Allow-Headers'] = (
            'Content-Type, Authorization, X-Requested-With, '
            'X-HMAC-Signature, X-Timestamp, X-Nonce'
        )
        response['Access-Control-Max-Age'] = '86400'  # 24 hours
        
        return response
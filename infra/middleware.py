"""
Security and infrastructure middleware for SOAPify.
Only HMACMiddleware is kept; CORS and rate-limiting are handled by
django-cors-headers and DRF throttling respectively.
"""

import hashlib
import hmac
import time
import re

from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache


class HMACMiddleware(MiddlewareMixin):
    """
    Enforces HMAC verification on configured paths (HMAC_ENFORCE_PATHS).

    Required headers:
      - X-Signature: hex-encoded HMAC-SHA256
      - X-Timestamp: unix epoch seconds
      - X-Nonce: unique nonce per request

    Canonical message to sign:
      METHOD|PATH|QUERY_STRING|BODY|TIMESTAMP|NONCE
    """

    def process_request(self, request):
        enforce_patterns = getattr(settings, 'HMAC_ENFORCE_PATHS', [])
        if not any(re.match(pattern, request.path) for pattern in enforce_patterns):
            return None

        # Optional config with sensible defaults
        max_skew = int(getattr(settings, 'HMAC_MAX_SKEW_SECONDS', 300))      # 5 minutes
        nonce_ttl = int(getattr(settings, 'HMAC_NONCE_TTL_SECONDS', 600))    # 10 minutes
        allowed_methods = set(getattr(
            settings, 'HMAC_ALLOWED_METHODS', {'POST', 'PUT', 'PATCH', 'DELETE'}
        ))

        if allowed_methods and request.method.upper() not in allowed_methods:
            return JsonResponse(
                {'error': 'Method not allowed for HMAC-protected endpoint'},
                status=405
            )

        signature = request.headers.get('X-Signature')
        timestamp = request.headers.get('X-Timestamp')
        nonce = request.headers.get('X-Nonce')

        if not (signature and timestamp and nonce):
            return JsonResponse({
                'error': 'Missing HMAC headers',
                'required_headers': ['X-Signature', 'X-Timestamp', 'X-Nonce']
            }, status=401)

        # Timestamp check
        try:
            ts_float = float(timestamp)
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Invalid timestamp format'}, status=401)

        if abs(time.time() - ts_float) > max_skew:
            return JsonResponse({'error': 'Request timestamp outside allowed window'}, status=401)

        # Replay protection via nonce in cache (scoped by path)
        nonce_key = f"hmac_nonce:{request.path}:{nonce}"
        if cache.get(nonce_key):
            return JsonResponse({'error': 'Nonce already used'}, status=401)
        cache.set(nonce_key, True, timeout=nonce_ttl)

        # Shared secret
        shared_secret = getattr(settings, 'HMAC_SHARED_SECRET', None)
        if not shared_secret:
            return JsonResponse({'error': 'HMAC not configured'}, status=500)

        # Canonical message
        method = request.method.upper()
        path = request.path
        query = request.META.get('QUERY_STRING', '')
        body_bytes = request.body or b''
        body = body_bytes.decode('utf-8', errors='replace')

        message = f"{method}|{path}|{query}|{body}|{int(ts_float)}|{nonce}"

        # Calculate expected signature
        expected_signature = hmac.new(
            key=shared_secret.encode('utf-8'),
            msg=message.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            return JsonResponse({'error': 'Invalid HMAC signature'}, status=401)

        return None

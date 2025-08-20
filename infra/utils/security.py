import hmac
import hashlib
import secrets
import time
from typing import Optional
from django.contrib.auth.hashers import make_password, check_password


def generate_hmac_signature(
    method: str,
    path: str,
    timestamp: str,
    nonce: str,
    body: Optional[str] = None,
    secret_key: str = None
) -> str:
    """
    Generate HMAC signature for API requests
    
    Args:
        method: HTTP method
        path: Request path
        timestamp: Request timestamp
        nonce: Unique nonce
        body: Request body (optional)
        secret_key: Secret key for signing
        
    Returns:
        HMAC signature as hex string
    """
    from django.conf import settings
    
    if not secret_key:
        secret_key = getattr(settings, 'HMAC_SECRET_KEY', settings.SECRET_KEY)
    
    # Build message to sign
    message = f"{method}:{path}:{timestamp}:{nonce}"
    if body:
        message += f":{body}"
    
    # Generate signature
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return signature


def generate_nonce() -> str:
    """Generate a unique nonce for requests"""
    return secrets.token_hex(16)


def hash_password(password: str) -> str:
    """Hash a password using Django's password hasher"""
    return make_password(password)


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a hash"""
    return check_password(password, hashed)


def generate_api_key() -> str:
    """Generate a secure API key"""
    return secrets.token_urlsafe(32)


def generate_otp() -> str:
    """Generate a 6-digit OTP"""
    return str(secrets.randbelow(900000) + 100000)


def is_timestamp_valid(timestamp: float, window: int = 300) -> bool:
    """
    Check if a timestamp is within an acceptable window
    
    Args:
        timestamp: Timestamp to check
        window: Acceptable window in seconds (default 5 minutes)
        
    Returns:
        True if timestamp is valid
    """
    current = time.time()
    return abs(current - timestamp) <= window
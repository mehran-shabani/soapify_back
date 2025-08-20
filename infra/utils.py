"""
Infrastructure utilities for SOAPify.
"""
import hashlib
import hmac
import time
import uuid
from datetime import datetime, timedelta
from urllib.parse import quote

import boto3
from django.conf import settings
from django.core.cache import cache


def generate_presigned_url(bucket_name, object_key, expiration=3600, http_method='PUT'):
    """
    Generate a presigned URL for S3 operations.
    
    Args:
        bucket_name: S3 bucket name
        object_key: S3 object key
        expiration: URL expiration in seconds (default: 1 hour)
        http_method: HTTP method (PUT for upload, GET for download)
    
    Returns:
        dict: Contains presigned URL and fields
    """
    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
        endpoint_url=settings.AWS_S3_ENDPOINT_URL
    )
    
    try:
        if http_method == 'PUT':
            response = s3_client.generate_presigned_post(
                Bucket=bucket_name,
                Key=object_key,
                ExpiresIn=expiration,
                Conditions=[
                    ['content-length-range', 1, 26214400]  # 1 byte to 25MB
                ]
            )
            return {
                'url': response['url'],
                'fields': response['fields']
            }
        else:
            url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': object_key},
                ExpiresIn=expiration
            )
            return {'url': url}
    
    except Exception as e:
        raise Exception(f"Failed to generate presigned URL: {str(e)}")


def calculate_file_hash(file_content):
    """Calculate SHA256 hash of file content."""
    return hashlib.sha256(file_content).hexdigest()


def generate_idempotency_key():
    """Generate a unique idempotency key."""
    return str(uuid.uuid4())


def create_hmac_signature(message, secret):
    """Create HMAC-SHA256 signature."""
    return hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


def verify_hmac_signature(message, signature, secret):
    """Verify HMAC-SHA256 signature."""
    expected_signature = create_hmac_signature(message, secret)
    return hmac.compare_digest(signature, expected_signature)


def cache_key_generator(prefix, *args):
    """Generate a cache key with prefix and arguments."""
    key_parts = [str(arg) for arg in args]
    return f"{prefix}:{'|'.join(key_parts)}"


def get_or_set_cache(key, callable_func, timeout=3600):
    """Get from cache or set with callable function result."""
    result = cache.get(key)
    if result is None:
        result = callable_func()
        cache.set(key, result, timeout=timeout)
    return result


def safe_int(value, default=0):
    """Safely convert value to integer."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value, default=0.0):
    """Safely convert value to float."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def truncate_text(text, max_length=100):
    """Truncate text to maximum length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + '...'


def format_file_size(size_bytes):
    """Format file size in human readable format."""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"


def validate_audio_file(file_obj):
    """
    Validate audio file format and size.
    
    Args:
        file_obj: Django UploadedFile object
    
    Returns:
        tuple: (is_valid, error_message)
    """
    # Check file size (max 25MB)
    if file_obj.size > 26214400:
        return False, "File size exceeds 25MB limit"
    
    # Check file extension
    allowed_extensions = ['.mp3', '.wav', '.m4a', '.ogg', '.flac']
    file_extension = file_obj.name.lower().split('.')[-1]
    if f'.{file_extension}' not in allowed_extensions:
        return False, f"File type not supported. Allowed: {', '.join(allowed_extensions)}"
    
    # Check MIME type
    allowed_mime_types = [
        'audio/mpeg', 'audio/wav', 'audio/mp4', 'audio/ogg', 'audio/flac'
    ]
    if hasattr(file_obj, 'content_type') and file_obj.content_type not in allowed_mime_types:
        return False, f"MIME type not supported: {file_obj.content_type}"
    
    return True, None


class TimestampMixin:
    """Mixin to add timestamp functionality to models."""
    
    @property
    def created_at_formatted(self):
        """Format created_at timestamp."""
        if hasattr(self, 'created_at'):
            return self.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')
        return None
    
    @property
    def updated_at_formatted(self):
        """Format updated_at timestamp."""
        if hasattr(self, 'updated_at'):
            return self.updated_at.strftime('%Y-%m-%d %H:%M:%S UTC')
        return None


def retry_with_backoff(func, max_retries=3, backoff_factor=2):
    """
    Retry function with exponential backoff.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retries
        backoff_factor: Backoff multiplier
    
    Returns:
        Function result or raises last exception
    """
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries:
                raise e
            
            wait_time = backoff_factor ** attempt
            time.sleep(wait_time)
    
    raise Exception("Max retries exceeded")
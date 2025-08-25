"""
Utility functions for Soapify infrastructure
"""

import os
import hashlib
import uuid
from datetime import datetime, timedelta
import pytz
from typing import Optional, Dict, Any, List, Tuple

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone


def generate_presigned_url(bucket_name, object_key, expiration=3600, http_method='PUT'):
    """
    Generate a presigned URL for S3 operations.
    
    Args:
        bucket_name: S3 bucket name
        object_key: S3 object key
        expiration: URL expiration time in seconds
        http_method: HTTP method (PUT for upload, GET for download)
    
    Returns:
        dict: Contains presigned URL and fields
    """
    # استفاده از MinIO client
    from uploads.minio import get_minio_client
    minio_client = get_minio_client()
    
    try:
        if http_method == 'PUT':
            response = minio_client.generate_presigned_post(
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
            url = minio_client.generate_presigned_url(
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


def generate_unique_id():
    """Generate a unique identifier."""
    return str(uuid.uuid4())


def get_current_timestamp():
    """Get current UTC timestamp."""
    return timezone.now()


def format_datetime(dt, format_string='%Y-%m-%d %H:%M:%S'):
    """Format datetime object to string."""
    if dt:
        return dt.strftime(format_string)
    return None


def parse_datetime(date_string, format_string='%Y-%m-%d %H:%M:%S'):
    """Parse string to datetime object."""
    try:
        return datetime.strptime(date_string, format_string)
    except (ValueError, TypeError):
        return None


def get_cache_key(prefix, *args):
    """Generate cache key with prefix."""
    parts = [str(prefix)] + [str(arg) for arg in args]
    return ':'.join(parts)


def set_cache_with_timeout(key, value, timeout=None):
    """Set cache with optional timeout."""
    if timeout is None:
        timeout = getattr(settings, 'DEFAULT_CACHE_TIMEOUT', 3600)
    cache.set(key, value, timeout)


def get_from_cache(key, default=None):
    """Get value from cache with default."""
    return cache.get(key, default)


def delete_from_cache(key):
    """Delete key from cache."""
    cache.delete(key)


def batch_process(items, batch_size=100):
    """Process items in batches."""
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]


def retry_with_backoff(func, max_retries=3, backoff_factor=2):
    """Retry function with exponential backoff."""
    import time
    
    for retry in range(max_retries):
        try:
            return func()
        except Exception as e:
            if retry == max_retries - 1:
                raise
            time.sleep(backoff_factor ** retry)


def sanitize_filename(filename):
    """Sanitize filename for safe storage."""
    import re
    # Remove special characters
    filename = re.sub(r'[^\w\s.-]', '', filename)
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    # Remove multiple underscores
    filename = re.sub(r'_+', '_', filename)
    return filename.strip('._')


def get_file_extension(filename):
    """Get file extension from filename."""
    return os.path.splitext(filename)[1].lower()


def is_valid_email(email):
    """Validate email format."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def truncate_string(text, max_length=100, suffix='...'):
    """Truncate string to specified length."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def get_client_ip(request):
    """Get client IP from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def calculate_age(birth_date):
    """Calculate age from birth date."""
    today = datetime.now().date()
    age = today.year - birth_date.year
    if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
        age -= 1
    return age


def format_file_size(size_in_bytes):
    """Format file size in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} PB"


def generate_slug(text):
    """Generate URL-friendly slug from text."""
    import re
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')


def merge_dicts(dict1, dict2):
    """Deep merge two dictionaries."""
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result
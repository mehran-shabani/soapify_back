# uploads/utils.py
"""
Utility functions for MinIO file operations
استفاده در سایر app ها:
    from uploads.utils import save_uploaded_file, get_file_url, delete_file
"""

from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
from typing import Optional, Union, BinaryIO
import os
import mimetypes
from datetime import datetime

from .minio import (
    get_minio_client, 
    get_presigned_url as _get_presigned_url,
    upload_file_to_minio as _upload_file_to_minio,
    delete_file_from_minio as _delete_file_from_minio,
    list_files_in_folder as _list_files_in_folder,
    get_bucket_name
)


def save_uploaded_file(
    file, 
    folder: str = 'uploads',
    filename: Optional[str] = None,
    prefix_date: bool = True
) -> str:
    """
    ذخیره فایل آپلود شده در MinIO
    
    Args:
        file: فایل آپلود شده (Django UploadedFile object)
        folder: پوشه مقصد (پیش‌فرض: uploads)
        filename: نام فایل (اختیاری، اگر نباشد از نام اصلی استفاده می‌شود)
        prefix_date: آیا تاریخ به مسیر اضافه شود (پیش‌فرض: True)
    
    Returns:
        URL کامل فایل ذخیره شده
    
    Example:
        url = save_uploaded_file(request.FILES['document'], folder='documents')
    """
    if not filename:
        filename = file.name
    
    # ساخت مسیر کامل
    if prefix_date:
        date_path = datetime.now().strftime('%Y/%m/%d')
        path = f"{folder}/{date_path}/{filename}"
    else:
        path = f"{folder}/{filename}"
    
    # ذخیره با استفاده از Django storage
    saved_path = default_storage.save(path, file)
    
    # برگرداندن URL کامل
    return default_storage.url(saved_path)


def save_file_from_content(
    content: Union[str, bytes],
    filename: str,
    folder: str = 'uploads',
    prefix_date: bool = True
) -> str:
    """
    ذخیره محتوا به عنوان فایل در MinIO
    
    Args:
        content: محتوای فایل (string یا bytes)
        filename: نام فایل
        folder: پوشه مقصد
        prefix_date: آیا تاریخ به مسیر اضافه شود
    
    Returns:
        URL کامل فایل ذخیره شده
    
    Example:
        url = save_file_from_content("Hello World", "test.txt", folder="texts")
    """
    if isinstance(content, str):
        content = content.encode('utf-8')
    
    file = ContentFile(content, name=filename)
    return save_uploaded_file(file, folder=folder, filename=filename, prefix_date=prefix_date)


def get_file_url(
    path: str,
    expiration: int = 3600,
    bucket_name: Optional[str] = None
) -> str:
    """
    دریافت URL امضا شده برای دسترسی به فایل
    
    Args:
        path: مسیر فایل در MinIO
        expiration: مدت اعتبار URL به ثانیه (پیش‌فرض: 1 ساعت)
        bucket_name: نام bucket (اختیاری)
    
    Returns:
        URL امضا شده
    
    Example:
        secure_url = get_file_url('documents/2024/01/15/report.pdf', expiration=7200)
    """
    return _get_presigned_url(path, bucket_name=bucket_name, expiration=expiration)


def get_public_url(path: str) -> str:
    """
    دریافت URL عمومی فایل (بدون امضا)
    
    Args:
        path: مسیر فایل در MinIO
    
    Returns:
        URL عمومی
    
    Example:
        public_url = get_public_url('images/logo.png')
    """
    return f"{settings.MINIO_ENDPOINT_URL}/{settings.MINIO_MEDIA_BUCKET}/{path}"


def delete_file(path: str) -> bool:
    """
    حذف فایل از MinIO
    
    Args:
        path: مسیر فایل برای حذف
    
    Returns:
        True در صورت موفقیت، False در غیر این صورت
    
    Example:
        success = delete_file('documents/old-report.pdf')
    """
    return default_storage.delete(path)


def delete_file_by_url(url: str) -> bool:
    """
    حذف فایل با استفاده از URL آن
    
    Args:
        url: URL کامل فایل
    
    Returns:
        True در صورت موفقیت، False در غیر این صورت
    """
    # استخراج path از URL
    base_url = f"{settings.MINIO_ENDPOINT_URL}/{settings.MINIO_MEDIA_BUCKET}/"
    if url.startswith(base_url):
        path = url[len(base_url):]
        return delete_file(path)
    return False


def file_exists(path: str) -> bool:
    """
    بررسی وجود فایل
    
    Args:
        path: مسیر فایل
    
    Returns:
        True اگر فایل وجود داشته باشد
    """
    return default_storage.exists(path)


def get_file_size(path: str) -> int:
    """
    دریافت اندازه فایل به بایت
    
    Args:
        path: مسیر فایل
    
    Returns:
        اندازه فایل به بایت
    """
    return default_storage.size(path)


def list_files(
    folder: str,
    recursive: bool = False
) -> list[dict]:
    """
    لیست فایل‌های موجود در یک پوشه
    
    Args:
        folder: مسیر پوشه
        recursive: آیا زیرپوشه‌ها هم بررسی شوند
    
    Returns:
        لیست فایل‌ها با اطلاعات آن‌ها
    
    Example:
        files = list_files('documents/2024/01')
    """
    return _list_files_in_folder(folder, bucket_name=get_bucket_name())


def get_file_info(path: str) -> dict:
    """
    دریافت اطلاعات کامل یک فایل
    
    Args:
        path: مسیر فایل
    
    Returns:
        دیکشنری حاوی اطلاعات فایل
    """
    if not file_exists(path):
        return None
    
    return {
        'path': path,
        'size': get_file_size(path),
        'url': get_public_url(path),
        'modified_time': default_storage.get_modified_time(path),
        'content_type': mimetypes.guess_type(path)[0] or 'application/octet-stream'
    }


def move_file(old_path: str, new_path: str) -> bool:
    """
    جابجایی فایل به مسیر جدید
    
    Args:
        old_path: مسیر فعلی فایل
        new_path: مسیر جدید
    
    Returns:
        True در صورت موفقیت
    """
    try:
        # خواندن فایل
        with default_storage.open(old_path, 'rb') as f:
            content = f.read()
        
        # ذخیره در مسیر جدید
        default_storage.save(new_path, ContentFile(content))
        
        # حذف فایل قدیمی
        default_storage.delete(old_path)
        
        return True
    except Exception:
        return False


def copy_file(source_path: str, dest_path: str) -> bool:
    """
    کپی فایل به مسیر جدید
    
    Args:
        source_path: مسیر فایل مبدا
        dest_path: مسیر مقصد
    
    Returns:
        True در صورت موفقیت
    """
    try:
        # خواندن فایل
        with default_storage.open(source_path, 'rb') as f:
            content = f.read()
        
        # ذخیره در مسیر جدید
        default_storage.save(dest_path, ContentFile(content))
        
        return True
    except Exception:
        return False


# Export all utility functions
__all__ = [
    # ذخیره و آپلود
    'save_uploaded_file',
    'save_file_from_content',
    
    # دریافت URL
    'get_file_url',
    'get_public_url',
    
    # حذف
    'delete_file',
    'delete_file_by_url',
    
    # بررسی و اطلاعات
    'file_exists',
    'get_file_size',
    'get_file_info',
    'list_files',
    
    # جابجایی و کپی
    'move_file',
    'copy_file',
    
    # دسترسی مستقیم به توابع MinIO (در صورت نیاز)
    'get_minio_client',
]
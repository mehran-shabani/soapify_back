# uploads/minio.py
from __future__ import annotations

from django.conf import settings
import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from typing import Optional, Dict, Any


def get_minio_client():
    """
    ساخت boto3 client برای اتصال به MinIO
    """
    cfg = BotoConfig(
        s3={"addressing_style": "path"},  # MinIO از path-style استفاده می‌کند
        signature_version="s3v4",
    )
    return boto3.client(
        "s3",
        endpoint_url=settings.MINIO_ENDPOINT_URL,
        region_name=settings.MINIO_REGION_NAME or "us-east-1",
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        config=cfg,
    )


def get_bucket_name() -> str:
    """
    دریافت نام bucket از تنظیمات
    """
    if not settings.MINIO_MEDIA_BUCKET:
        raise RuntimeError("MINIO_MEDIA_BUCKET is required for MinIO uploads")
    return settings.MINIO_MEDIA_BUCKET


def build_object_key(folder: str, filename: str, session_id: Optional[str] = None) -> str:
    """
    ساخت کلید شیء برای ذخیره در MinIO
    
    Args:
        folder: پوشه اصلی (مثل audio_sessions, documents, images)
        filename: نام فایل
        session_id: شناسه جلسه (اختیاری)
    
    Returns:
        کلید کامل برای ذخیره در MinIO
    """
    if session_id:
        return f"{folder}/{session_id}/{filename}"
    return f"{folder}/{filename}"


def ensure_bucket_exists(bucket_name: Optional[str] = None) -> None:
    """
    اطمینان از وجود bucket و در صورت نبود، ایجاد آن
    """
    client = get_minio_client()
    bucket = bucket_name or get_bucket_name()

    try:
        client.head_bucket(Bucket=bucket)
        return
    except ClientError as e:
        code = (e.response.get("Error", {}).get("Code") or "").lower()
        if code not in ("404", "notfound", "nosuchbucket"):
            raise

    # ایجاد bucket
    client.create_bucket(Bucket=bucket)
    
    # تنظیم policy برای دسترسی عمومی به خواندن (برای فایل‌های media)
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket}/*"
            }
        ]
    }
    
    client.put_bucket_policy(
        Bucket=bucket,
        Policy=json.dumps(policy)
    )


def upload_file_to_minio(
    file_obj,
    object_key: str,
    bucket_name: Optional[str] = None,
    content_type: Optional[str] = None,
    metadata: Optional[Dict[str, str]] = None
) -> str:
    """
    آپلود فایل به MinIO
    
    Args:
        file_obj: شیء فایل برای آپلود
        object_key: کلید (مسیر) فایل در MinIO
        bucket_name: نام bucket (اختیاری، از تنظیمات خوانده می‌شود)
        content_type: نوع محتوا (اختیاری)
        metadata: متادیتای اضافی (اختیاری)
    
    Returns:
        URL کامل فایل آپلود شده
    """
    client = get_minio_client()
    bucket = bucket_name or get_bucket_name()
    
    # تنظیمات آپلود
    extra_args = {}
    if content_type:
        extra_args['ContentType'] = content_type
    if metadata:
        extra_args['Metadata'] = metadata
    
    # آپلود فایل
    client.upload_fileobj(
        file_obj,
        bucket,
        object_key,
        ExtraArgs=extra_args
    )
    
    # برگرداندن URL
    return f"{settings.MINIO_ENDPOINT_URL}/{bucket}/{object_key}"


def get_presigned_url(
    object_key: str,
    bucket_name: Optional[str] = None,
    expiration: int = 3600
) -> str:
    """
    ایجاد URL امضا شده برای دسترسی موقت به فایل
    
    Args:
        object_key: کلید فایل در MinIO
        bucket_name: نام bucket (اختیاری)
        expiration: مدت اعتبار URL به ثانیه (پیش‌فرض: 1 ساعت)
    
    Returns:
        URL امضا شده
    """
    client = get_minio_client()
    bucket = bucket_name or get_bucket_name()
    
    return client.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket, 'Key': object_key},
        ExpiresIn=expiration
    )


def delete_file_from_minio(
    object_key: str,
    bucket_name: Optional[str] = None
) -> bool:
    """
    حذف فایل از MinIO
    
    Args:
        object_key: کلید فایل برای حذف
        bucket_name: نام bucket (اختیاری)
    
    Returns:
        True در صورت موفقیت، False در غیر این صورت
    """
    client = get_minio_client()
    bucket = bucket_name or get_bucket_name()
    
    try:
        client.delete_object(Bucket=bucket, Key=object_key)
        return True
    except ClientError:
        return False


def list_files_in_folder(
    folder: str,
    bucket_name: Optional[str] = None
) -> list[dict]:
    """
    لیست فایل‌های موجود در یک پوشه
    
    Args:
        folder: مسیر پوشه
        bucket_name: نام bucket (اختیاری)
    
    Returns:
        لیست فایل‌ها با اطلاعات آن‌ها
    """
    client = get_minio_client()
    bucket = bucket_name or get_bucket_name()
    
    files = []
    
    try:
        response = client.list_objects_v2(
            Bucket=bucket,
            Prefix=folder + '/' if not folder.endswith('/') else folder
        )
        
        for obj in response.get('Contents', []):
            files.append({
                'key': obj['Key'],
                'size': obj['Size'],
                'last_modified': obj['LastModified'],
                'etag': obj['ETag']
            })
    except ClientError:
        pass
    
    return files


# Import json for policy
import json
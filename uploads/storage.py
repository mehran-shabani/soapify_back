# uploads/storage.py
from django.core.files.storage import Storage
from django.conf import settings
from django.utils.deconstruct import deconstructible
from django.utils.encoding import filepath_to_uri
from django.core.files.base import File
from django.core.exceptions import SuspiciousFileOperation
from django.utils.crypto import get_random_string
import os
import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from datetime import datetime
import mimetypes


@deconstructible
class MinioMediaStorage(Storage):
    """
    Custom storage backend برای ذخیره فایل‌های media در MinIO
    """
    
    def __init__(self, bucket_name=None, endpoint_url=None, access_key=None, 
                 secret_key=None, region_name=None, secure=True):
        self.bucket_name = bucket_name or settings.MINIO_MEDIA_BUCKET
        self.endpoint_url = endpoint_url or settings.MINIO_ENDPOINT_URL
        self.access_key = access_key or settings.MINIO_ACCESS_KEY
        self.secret_key = secret_key or settings.MINIO_SECRET_KEY
        self.region_name = region_name or getattr(settings, 'MINIO_REGION_NAME', 'us-east-1')
        self.secure = secure
        
        # ایجاد client
        self._client = None
        
    @property
    def client(self):
        """Lazy initialization of boto3 client"""
        if self._client is None:
            cfg = BotoConfig(
                s3={"addressing_style": "path"},
                signature_version="s3v4",
            )
            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                region_name=self.region_name,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                config=cfg,
            )
            # اطمینان از وجود bucket
            self._ensure_bucket_exists()
        return self._client
    
    def _ensure_bucket_exists(self):
        """اطمینان از وجود bucket"""
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            code = (e.response.get("Error", {}).get("Code") or "").lower()
            if code in ("404", "notfound", "nosuchbucket"):
                # ایجاد bucket
                self.client.create_bucket(Bucket=self.bucket_name)
                
                # تنظیم policy برای دسترسی عمومی
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": "*"},
                            "Action": "s3:GetObject",
                            "Resource": f"arn:aws:s3:::{self.bucket_name}/*"
                        }
                    ]
                }
                
                import json
                self.client.put_bucket_policy(
                    Bucket=self.bucket_name,
                    Policy=json.dumps(policy)
                )
    
    def _save(self, name, content):
        """ذخیره فایل در MinIO"""
        # تولید نام یکتا اگر فایل وجود دارد
        name = self.get_available_name(name)
        
        # تشخیص content type
        content_type = getattr(content, 'content_type', None)
        if not content_type:
            content_type, _ = mimetypes.guess_type(name)
            if not content_type:
                content_type = 'application/octet-stream'
        
        # آپلود فایل
        try:
            self.client.upload_fileobj(
                content,
                self.bucket_name,
                name,
                ExtraArgs={
                    'ContentType': content_type,
                    'Metadata': {
                        'uploaded_at': datetime.now().isoformat(),
                    }
                }
            )
        except Exception as e:
            raise IOError(f"Failed to save file to MinIO: {str(e)}")
        
        return name
    
    def _open(self, name, mode='rb'):
        """باز کردن فایل از MinIO"""
        if 'w' in mode:
            raise ValueError("MinIO storage doesn't support write mode")
        
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=name)
            return File(response['Body'], name=name)
        except ClientError as e:
            if e.response.get('Error', {}).get('Code') == 'NoSuchKey':
                raise FileNotFoundError(f"File not found: {name}")
            raise
    
    def delete(self, name):
        """حذف فایل از MinIO"""
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=name)
        except ClientError:
            pass  # اگر فایل وجود نداشت، نادیده بگیر
    
    def exists(self, name):
        """بررسی وجود فایل"""
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=name)
            return True
        except ClientError:
            return False
    
    def listdir(self, path):
        """لیست فایل‌ها و دایرکتوری‌ها در یک مسیر"""
        path = path.rstrip('/')
        if path:
            path += '/'
        
        directories = set()
        files = []
        
        paginator = self.client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=self.bucket_name, Prefix=path, Delimiter='/')
        
        for page in pages:
            # دایرکتوری‌ها
            for prefix in page.get('CommonPrefixes', []):
                directories.add(prefix['Prefix'].rstrip('/').split('/')[-1])
            
            # فایل‌ها
            for obj in page.get('Contents', []):
                key = obj['Key']
                if key != path:  # خود دایرکتوری را شامل نشود
                    filename = key[len(path):]
                    if '/' not in filename:  # فقط فایل‌های مستقیم
                        files.append(filename)
        
        return list(directories), files
    
    def size(self, name):
        """اندازه فایل"""
        try:
            response = self.client.head_object(Bucket=self.bucket_name, Key=name)
            return response['ContentLength']
        except ClientError:
            raise FileNotFoundError(f"File not found: {name}")
    
    def url(self, name):
        """URL عمومی فایل"""
        # URL ساده برای دسترسی عمومی
        return f"{self.endpoint_url}/{self.bucket_name}/{name}"
    
    def get_accessed_time(self, name):
        """زمان آخرین دسترسی (MinIO این را پشتیبانی نمی‌کند)"""
        return self.get_modified_time(name)
    
    def get_created_time(self, name):
        """زمان ایجاد"""
        return self.get_modified_time(name)
    
    def get_modified_time(self, name):
        """زمان آخرین تغییر"""
        try:
            response = self.client.head_object(Bucket=self.bucket_name, Key=name)
            return response['LastModified']
        except ClientError:
            raise FileNotFoundError(f"File not found: {name}")
    
    def get_available_name(self, name, max_length=None):
        """تولید نام یکتا برای فایل"""
        dir_name, file_name = os.path.split(name)
        file_root, file_ext = os.path.splitext(file_name)
        
        # اگر فایل وجود ندارد، همان نام را برگردان
        if not self.exists(name):
            return name
        
        # تولید نام جدید با افزودن رشته تصادفی
        while True:
            random_suffix = get_random_string(7)
            new_name = os.path.join(dir_name, f"{file_root}_{random_suffix}{file_ext}")
            
            if not self.exists(new_name):
                return new_name
    
    def generate_filename(self, filename):
        """
        تولید نام فایل نهایی
        می‌توانید این متد را override کنید تا ساختار دلخواه خود را ایجاد کنید
        """
        # حذف کاراکترهای غیرمجاز
        filename = filename.replace('\\', '/')
        
        # می‌توانید اینجا logic دلخواه خود را اضافه کنید
        # مثلاً افزودن تاریخ به مسیر
        today = datetime.now().strftime('%Y/%m/%d')
        return f"uploads/{today}/{filename}"
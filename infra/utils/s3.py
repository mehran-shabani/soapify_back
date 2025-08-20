import boto3
import hashlib
from django.conf import settings
from botocore.exceptions import ClientError
from typing import Optional, Dict, Any


class S3Utils:
    """Utilities for S3 operations"""
    
    def __init__(self):
        self.client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    
    def generate_presigned_url(
        self, 
        key: str, 
        operation: str = 'put_object',
        expiration: int = 3600,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Generate a pre-signed URL for S3 operations
        
        Args:
            key: S3 object key
            operation: S3 operation (put_object, get_object)
            expiration: URL expiration time in seconds
            content_type: Content type for upload
            metadata: Additional metadata for the object
            
        Returns:
            Dict with url and fields for upload
        """
        try:
            params = {
                'Bucket': self.bucket_name,
                'Key': key,
            }
            
            if operation == 'put_object':
                if content_type:
                    params['ContentType'] = content_type
                if metadata:
                    params['Metadata'] = metadata
            
            url = self.client.generate_presigned_url(
                ClientMethod=operation,
                Params=params,
                ExpiresIn=expiration
            )
            
            return {
                'url': url,
                'fields': {
                    'key': key,
                    'bucket': self.bucket_name
                }
            }
            
        except ClientError as e:
            raise Exception(f"Error generating presigned URL: {str(e)}")
    
    def verify_upload(self, key: str, etag: str, sha256: str) -> bool:
        """
        Verify an uploaded file
        
        Args:
            key: S3 object key
            etag: Expected ETag
            sha256: Expected SHA256 hash
            
        Returns:
            True if verification passes
        """
        try:
            # Get object metadata
            response = self.client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            # Verify ETag
            actual_etag = response['ETag'].strip('"')
            if actual_etag != etag.strip('"'):
                return False
            
            # Download and verify SHA256
            obj = self.client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            content = obj['Body'].read()
            actual_sha256 = hashlib.sha256(content).hexdigest()
            
            return actual_sha256 == sha256
            
        except ClientError:
            return False
    
    def delete_object(self, key: str) -> bool:
        """Delete an object from S3"""
        try:
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return True
        except ClientError:
            return False


def generate_presigned_url(
    key: str,
    operation: str = 'put_object',
    expiration: int = 3600,
    **kwargs
) -> Dict[str, Any]:
    """Convenience function for generating presigned URLs"""
    s3_utils = S3Utils()
    return s3_utils.generate_presigned_url(
        key=key,
        operation=operation,
        expiration=expiration,
        **kwargs
    )
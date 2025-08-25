from django.core.management.base import BaseCommand
from botocore.exceptions import ClientError
from django.conf import settings

from uploads.minio import get_minio_client, get_bucket_name

class Command(BaseCommand):
    help = "Create MinIO bucket if it does not exist"

    def handle(self, *args, **options):
        client = get_minio_client()
        bucket = get_bucket_name()

        # آیا وجود دارد؟
        try:
            client.head_bucket(Bucket=bucket)
            self.stdout.write(self.style.SUCCESS(f"Bucket '{bucket}' already exists ✅"))
            return
        except ClientError as e:
            code = (e.response.get("Error", {}).get("Code") or "").lower()
            if code not in ("404", "notfound", "nosuchbucket"):
                raise

        # ایجاد باکت
        client.create_bucket(Bucket=bucket)
        self.stdout.write(self.style.SUCCESS(f"Bucket '{bucket}' created successfully 🚀"))
        
        # تنظیم policy برای دسترسی عمومی
        import json
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": ["s3:GetObject"],
                    "Resource": f"arn:aws:s3:::{bucket}/*"
                }
            ]
        }
        
        client.put_bucket_policy(
            Bucket=bucket,
            Policy=json.dumps(policy)
        )
        self.stdout.write(self.style.SUCCESS(f"Public read policy set for '{bucket}' 🔓"))

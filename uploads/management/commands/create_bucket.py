from django.core.management.base import BaseCommand
from botocore.exceptions import ClientError
from django.conf import settings

from upload.s3 import get_s3_client, get_bucket_name

class Command(BaseCommand):
    help = "Create S3 bucket if it does not exist"

    def handle(self, *args, **options):
        client = get_s3_client()
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
        params = {"Bucket": bucket}
        region = getattr(settings, "S3_REGION_NAME", None)
        if region and region != "us-east-1":
            params["CreateBucketConfiguration"] = {"LocationConstraint": region}

        client.create_bucket(**params)
        self.stdout.write(self.style.SUCCESS(f"Bucket '{bucket}' created successfully 🚀"))

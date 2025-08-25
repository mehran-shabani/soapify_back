from django.core.management.base import BaseCommand
from botocore.exceptions import ClientError
from django.conf import settings
import json

from uploads.minio import get_minio_client


class Command(BaseCommand):
    help = "Setup MinIO buckets for media and static files"

    def add_arguments(self, parser):
        parser.add_argument(
            '--media-only',
            action='store_true',
            help='Only create media bucket',
        )
        parser.add_argument(
            '--static-only',
            action='store_true',
            help='Only create static bucket',
        )

    def create_bucket_with_policy(self, client, bucket_name, public=True):
        """ایجاد باکت و تنظیم policy"""
        # بررسی وجود باکت
        try:
            client.head_bucket(Bucket=bucket_name)
            self.stdout.write(
                self.style.WARNING(f"Bucket '{bucket_name}' already exists ⚠️")
            )
            return False
        except ClientError as e:
            code = (e.response.get("Error", {}).get("Code") or "").lower()
            if code not in ("404", "notfound", "nosuchbucket"):
                raise

        # ایجاد باکت
        try:
            client.create_bucket(Bucket=bucket_name)
            self.stdout.write(
                self.style.SUCCESS(f"Bucket '{bucket_name}' created successfully ✅")
            )
            
            # تنظیم policy برای دسترسی عمومی (اگر نیاز باشد)
            if public:
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": "*"},
                            "Action": ["s3:GetObject"],
                            "Resource": f"arn:aws:s3:::{bucket_name}/*"
                        }
                    ]
                }
                
                client.put_bucket_policy(
                    Bucket=bucket_name,
                    Policy=json.dumps(policy)
                )
                self.stdout.write(
                    self.style.SUCCESS(f"Public read policy set for '{bucket_name}' 🔓")
                )
            
            return True
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Failed to create bucket '{bucket_name}': {str(e)} ❌")
            )
            return False

    def handle(self, *args, **options):
        client = get_minio_client()
        
        media_only = options.get('media_only', False)
        static_only = options.get('static_only', False)
        
        buckets_to_create = []
        
        # تعیین باکت‌هایی که باید ساخته شوند
        if static_only:
            buckets_to_create.append({
                'name': settings.MINIO_STATIC_BUCKET,
                'public': True,
                'type': 'Static'
            })
        elif media_only:
            buckets_to_create.append({
                'name': settings.MINIO_MEDIA_BUCKET,
                'public': True,
                'type': 'Media'
            })
        else:
            # هر دو باکت
            buckets_to_create.extend([
                {
                    'name': settings.MINIO_MEDIA_BUCKET,
                    'public': True,
                    'type': 'Media'
                },
                {
                    'name': settings.MINIO_STATIC_BUCKET,
                    'public': True,
                    'type': 'Static'
                }
            ])
        
        self.stdout.write(self.style.MIGRATE_HEADING("Setting up MinIO buckets..."))
        self.stdout.write(f"MinIO Endpoint: {settings.MINIO_ENDPOINT_URL}")
        self.stdout.write("-" * 50)
        
        created_count = 0
        for bucket_info in buckets_to_create:
            self.stdout.write(f"\n{bucket_info['type']} bucket: {bucket_info['name']}")
            if self.create_bucket_with_policy(client, bucket_info['name'], bucket_info['public']):
                created_count += 1
        
        self.stdout.write("-" * 50)
        self.stdout.write(
            self.style.SUCCESS(f"\n✨ Setup complete! Created {created_count} new bucket(s).")
        )
        
        # نمایش URL های دسترسی
        self.stdout.write("\n📌 Access URLs:")
        if not static_only:
            self.stdout.write(f"   Media: {settings.MINIO_ENDPOINT_URL}/{settings.MINIO_MEDIA_BUCKET}/")
        if not media_only:
            self.stdout.write(f"   Static: {settings.MINIO_ENDPOINT_URL}/{settings.MINIO_STATIC_BUCKET}/")
        
        # راهنمای MinIO Console
        self.stdout.write("\n💡 MinIO Console:")
        self.stdout.write(f"   URL: http://localhost:9001")
        self.stdout.write(f"   Username: {settings.MINIO_ACCESS_KEY}")
        self.stdout.write(f"   Password: {settings.MINIO_SECRET_KEY}")
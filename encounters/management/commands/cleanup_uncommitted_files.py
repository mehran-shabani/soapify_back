"""
Management command to cleanup uncommitted audio files.
"""

import boto3
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from encounters.models import AudioChunk


class Command(BaseCommand):
    help = 'Cleanup uncommitted audio files older than specified time'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=2,
            help='Clean files older than this many hours (default: 2)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        hours = options['hours']
        dry_run = options['dry_run']
        
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        # Find uncommitted files older than cutoff time
        uncommitted_chunks = AudioChunk.objects.filter(
            status='uploaded',
            uploaded_at__lt=cutoff_time
        )
        
        if not uncommitted_chunks.exists():
            self.stdout.write(
                self.style.SUCCESS(f'No uncommitted files older than {hours} hours found.')
            )
            return
        
        # Initialize MinIO client
        from uploads.minio import get_minio_client
        minio_client = get_minio_client()
        
        deleted_count = 0
        error_count = 0
        
        for chunk in uncommitted_chunks:
            try:
                if dry_run:
                    self.stdout.write(f'Would delete: {chunk.file_path}')
                else:
                    # Delete from MinIO
                    minio_client.delete_object(
                        Bucket=settings.MINIO_MEDIA_BUCKET,
                        Key=chunk.file_path
                    )
                    
                    # Delete from database
                    chunk.delete()
                    
                    self.stdout.write(f'Deleted: {chunk.file_path}')
                
                deleted_count += 1
                
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'Error deleting {chunk.file_path}: {e}')
                )
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'Dry run complete. Would delete {deleted_count} files.')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Cleanup complete. Deleted {deleted_count} files, {error_count} errors.'
                )
            )

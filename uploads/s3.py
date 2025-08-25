# upload/s3.py
from __future__ import annotations

from django.conf import settings
import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError


def get_s3_client():
    """
    ساخت boto3 client بر اساس settings با پیشوند S3_
    """
    cfg = BotoConfig(
        s3={"addressing_style": settings.S3_ADDRESSING_STYLE},
        signature_version=settings.S3_SIGNATURE_VERSION,
    )
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        region_name=settings.S3_REGION_NAME,
        aws_access_key_id=settings.S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        config=cfg,
    )


def get_bucket_name() -> str:
    if not settings.S3_BUCKET_NAME:
        raise RuntimeError("S3_BUCKET_NAME is required for S3 uploads")
    return settings.S3_BUCKET_NAME


def build_object_key(session_id: str, filename: str) -> str:
    return f"audio_sessions/{session_id}/{filename}"


def ensure_bucket_exists() -> None:
    """
    اگر باکت وجود نداشت، بساز (برای اجرای یک‌باره از طریق management command)
    """
    client = get_s3_client()
    bucket = get_bucket_name()

    try:
        client.head_bucket(Bucket=bucket)
        return
    except ClientError as e:
        code = (e.response.get("Error", {}).get("Code") or "").lower()
        if code not in ("404", "notfound", "nosuchbucket"):
            raise

    params = {"Bucket": bucket}
    region = settings.S3_REGION_NAME
    if region and region != "us-east-1":
        params["CreateBucketConfiguration"] = {"LocationConstraint": region}

    client.create_bucket(**params)

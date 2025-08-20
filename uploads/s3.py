from __future__ import annotations

import os
from dataclasses import dataclass

import boto3


@dataclass
class S3Config:
    endpoint_url: str | None
    bucket_name: str
    region_name: str | None
    access_key_id: str | None
    secret_access_key: str | None


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("S3_ENDPOINT_URL") or None,
        region_name=os.getenv("S3_REGION_NAME") or None,
        aws_access_key_id=os.getenv("S3_ACCESS_KEY_ID") or None,
        aws_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY") or None,
    )


def get_bucket_name() -> str:
    bucket = os.getenv("S3_BUCKET_NAME")
    if not bucket:
        raise RuntimeError("S3_BUCKET_NAME is required for S3 uploads")
    return bucket


def build_object_key(session_id: str, filename: str) -> str:
    return f"audio_sessions/{session_id}/{filename}"


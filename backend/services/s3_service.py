"""
S3 helpers for SkinGraph Phase 4.

Buckets (us-east-1):
  skingraph-uploads   – raw label photos  (lifecycle: expire 1 day)
  skingraph-analyses  – saved JSON reports (permanent)
"""

import base64
import json
import logging
import os
import uuid
from datetime import datetime

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)

UPLOADS_BUCKET = "skingraph-uploads"
ANALYSES_BUCKET = "skingraph-analyses"


def _s3_client():
    return boto3.client(
        "s3",
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )


def upload_photo(image_base64: str, filename: str | None = None) -> str:
    """
    Decode base64 image and upload to skingraph-uploads.

    Returns the S3 key on success, or empty string on failure.
    The bucket lifecycle rule auto-deletes objects after 1 day.
    """
    if not filename:
        filename = f"{uuid.uuid4().hex}.jpg"

    try:
        image_bytes = base64.b64decode(image_base64)
        key = f"labels/{filename}"
        _s3_client().put_object(
            Bucket=UPLOADS_BUCKET,
            Key=key,
            Body=image_bytes,
            ContentType="image/jpeg",
        )
        logger.info(f"Uploaded photo → s3://{UPLOADS_BUCKET}/{key}")
        return key
    except (BotoCoreError, ClientError, Exception) as e:
        logger.warning(f"S3 photo upload failed: {e}")
        return ""


def save_analysis(product_name: str, skin_type: str, result_json: dict) -> str:
    """
    Persist analysis JSON to skingraph-analyses.

    Returns the S3 key on success, or empty string on failure.
    """
    try:
        safe = "".join(
            c if c.isalnum() or c in "-_" else "_"
            for c in product_name.lower()
        )
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        key = f"analyses/{safe}_{skin_type}_{ts}.json"
        _s3_client().put_object(
            Bucket=ANALYSES_BUCKET,
            Key=key,
            Body=json.dumps(result_json, indent=2).encode("utf-8"),
            ContentType="application/json",
        )
        logger.info(f"Saved analysis → s3://{ANALYSES_BUCKET}/{key}")
        return key
    except (BotoCoreError, ClientError, Exception) as e:
        logger.warning(f"S3 analysis save failed: {e}")
        return ""

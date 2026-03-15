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
    """
    if not filename:
        filename = f"{uuid.uuid4().hex}.jpg"

    try:
        image_bytes = base64.b64decode(image_base64)
        key = f"labels/{filename}"
        logger.info(
            f"S3 UPLOAD: bucket={UPLOADS_BUCKET}, key={key}, "
            f"image_size={len(image_bytes)} bytes, "
            f"region={os.getenv('AWS_REGION', 'us-east-1')}"
        )
        _s3_client().put_object(
            Bucket=UPLOADS_BUCKET,
            Key=key,
            Body=image_bytes,
            ContentType="image/jpeg",
        )
        logger.info(f"S3 UPLOAD SUCCESS: s3://{UPLOADS_BUCKET}/{key} ({len(image_bytes)} bytes)")
        return key
    except (BotoCoreError, ClientError) as e:
        logger.error(f"S3 UPLOAD FAILED (boto): bucket={UPLOADS_BUCKET}, error={e}")
        return ""
    except Exception as e:
        logger.error(f"S3 UPLOAD FAILED (unexpected): {e}")
        return ""


def save_analysis(product_name: str, skin_type: str, result_json: dict) -> str:
    """Persist analysis JSON to skingraph-analyses."""
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
        logger.info(f"S3 analysis saved → s3://{ANALYSES_BUCKET}/{key}")
        return key
    except (BotoCoreError, ClientError) as e:
        logger.warning(f"S3 analysis save failed (boto): {e}")
        return ""
    except Exception as e:
        logger.warning(f"S3 analysis save failed: {e}")
        return ""


def test_s3_connection() -> dict:
    """
    Diagnostic: upload a tiny test file to skingraph-uploads and verify.
    Returns status dict with success/failure info.
    """
    result = {
        "bucket": UPLOADS_BUCKET,
        "region": os.getenv("AWS_REGION", "us-east-1"),
        "aws_key_set": bool(os.getenv("AWS_ACCESS_KEY_ID")),
        "aws_secret_set": bool(os.getenv("AWS_SECRET_ACCESS_KEY")),
    }

    test_key = f"test/connectivity-{uuid.uuid4().hex[:8]}.txt"
    try:
        client = _s3_client()
        client.put_object(
            Bucket=UPLOADS_BUCKET,
            Key=test_key,
            Body=b"SkinGraph S3 connectivity test",
            ContentType="text/plain",
        )
        result["upload_success"] = True
        result["test_key"] = test_key
        logger.info(f"S3 TEST: upload succeeded → s3://{UPLOADS_BUCKET}/{test_key}")

        # Try to read it back
        resp = client.get_object(Bucket=UPLOADS_BUCKET, Key=test_key)
        body = resp["Body"].read()
        result["read_back_success"] = True
        result["read_back_size"] = len(body)

        # Clean up
        client.delete_object(Bucket=UPLOADS_BUCKET, Key=test_key)
        result["cleanup_success"] = True

    except (BotoCoreError, ClientError) as e:
        result["upload_success"] = False
        result["error"] = str(e)
        logger.error(f"S3 TEST FAILED: {e}")
    except Exception as e:
        result["upload_success"] = False
        result["error"] = str(e)
        logger.error(f"S3 TEST FAILED (unexpected): {e}")

    return result

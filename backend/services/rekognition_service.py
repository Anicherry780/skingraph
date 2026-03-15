"""
Rekognition helpers for SkinGraph Phase 4.
Used ONLY for skin type hints via label detection.
Product name comes from Textract, not Rekognition.
"""

import logging
import os

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)

UPLOADS_BUCKET = "skingraph-uploads"

# Rekognition label → skin type mapping
_LABEL_SKIN_MAP: dict[str, str] = {
    "Sunscreen": "combination",
    "Sun Screen": "combination",
    "Tanning": "combination",
    "Moisturizer": "dry",
    "Moisturiser": "dry",
    "Lotion": "dry",
    "Body Lotion": "dry",
    "Face Cream": "dry",
    "Skin Care": "combination",
    "Cosmetics": "combination",
    "Cream": "dry",
}

# Text keywords in label → skin type mapping
_TEXT_SKIN_MAP: dict[str, str] = {
    "oil control": "oily",
    "oil-free": "oily",
    "oily skin": "oily",
    "shine control": "oily",
    "mattifying": "oily",
    "matte": "oily",
    "dry skin": "dry",
    "hydrating": "dry",
    "moisture": "dry",
    "nourishing": "dry",
    "intensive": "dry",
    "sensitive skin": "sensitive",
    "sensitive": "sensitive",
    "gentle": "sensitive",
    "hypoallergenic": "sensitive",
    "calming": "sensitive",
    "soothing": "sensitive",
    "fragrance-free": "sensitive",
    "combination skin": "combination",
    "combination": "combination",
    "t-zone": "combination",
    "spf": "combination",
    "sunscreen": "combination",
    "sunblock": "combination",
}


def _rek_client():
    return boto3.client(
        "rekognition",
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )


def detect_product_from_s3(s3_key: str) -> dict:
    """
    Run Rekognition detectLabels + detectText on S3 object.
    Used ONLY for skin type hints. Product name comes from Textract.

    Returns:
        {
            "product_type":     str,           # top label name or "Skincare Product"
            "detected_labels":  list[str],     # top 5 label names
            "skin_type_hint":   str | None,    # first matched skin type
            "top_confidence":   float,
        }
    """
    rek = _rek_client()
    s3_doc = {"S3Object": {"Bucket": UPLOADS_BUCKET, "Name": s3_key}}

    detected_labels: list[str] = []
    product_type = "Skincare Product"
    top_confidence = 0.0
    skin_type_hint: str | None = None

    # ── detectLabels → skin type hint ───────────────────────────────────────
    try:
        resp = rek.detect_labels(
            Image=s3_doc,
            MaxLabels=10,
            MinConfidence=70.0,
        )
        labels = resp.get("Labels", [])
        detected_labels = [l["Name"] for l in labels[:5]]
        if labels:
            product_type = labels[0]["Name"]
            top_confidence = round(labels[0].get("Confidence", 0.0), 1)

        for label in labels:
            name = label.get("Name", "")
            if name in _LABEL_SKIN_MAP:
                skin_type_hint = _LABEL_SKIN_MAP[name]
                logger.info(f"Rekognition skin hint from label '{name}': {skin_type_hint}")
                break

        logger.info(f"Rekognition detectLabels: {detected_labels}")
    except (BotoCoreError, ClientError) as e:
        logger.warning(f"Rekognition detectLabels failed: {e}")
    except Exception as e:
        logger.warning(f"Rekognition detectLabels unexpected error: {e}")

    # ── detectText → skin type hint (if not already found) ──────────────────
    if not skin_type_hint:
        try:
            resp = rek.detect_text(Image=s3_doc)
            lines = [
                d["DetectedText"]
                for d in resp.get("TextDetections", [])
                if d.get("Type") == "LINE"
            ]
            full_text = " ".join(lines).lower()
            for kw, stype in _TEXT_SKIN_MAP.items():
                if kw in full_text:
                    skin_type_hint = stype
                    logger.info(f"Rekognition skin hint from text keyword '{kw}': {stype}")
                    break
            logger.info(f"Rekognition detectText: {len(lines)} lines, skin_type_hint={skin_type_hint}")
        except (BotoCoreError, ClientError) as e:
            logger.warning(f"Rekognition detectText failed: {e}")
        except Exception as e:
            logger.warning(f"Rekognition detectText unexpected error: {e}")

    return {
        "product_type": product_type,
        "detected_labels": detected_labels,
        "skin_type_hint": skin_type_hint,
        "top_confidence": top_confidence,
    }

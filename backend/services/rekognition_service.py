"""
Rekognition helpers for SkinGraph Phase 4.

Detects product type and skin-type hints from a product label photo
already uploaded to the skingraph-uploads S3 bucket.
"""

import logging
import os
import re

import boto3

logger = logging.getLogger(__name__)

UPLOADS_BUCKET = "skingraph-uploads"

SKIN_TYPE_KEYWORDS = {
    "oily": ["oil control", "oil-free", "oily", "shine", "mattifying", "matte", "pore"],
    "dry": ["dry", "hydrating", "moisture", "nourishing", "rich", "intensive moisture"],
    "sensitive": ["sensitive", "gentle", "hypoallergenic", "calming", "soothing", "fragrance-free"],
    "combination": ["combination", "balance", "t-zone", "normal to"],
}


def _rekognition_client():
    return boto3.client(
        "rekognition",
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )


def detect_product_from_s3(s3_key: str) -> dict:
    """
    Use Rekognition to detect product type and skin-type hints from a label photo.

    Returns:
        {
            "product_type": str,          # "Bottle", "Cosmetics", etc., or "Skincare Product"
            "detected_labels": list[str], # top 5 label names
            "skin_type_hint": str | None, # first skin type keyword found
            "top_confidence": float,      # confidence of first label
        }
    """
    rek = _rekognition_client()
    s3_obj = {"Bucket": UPLOADS_BUCKET, "Name": s3_key}

    detected_labels: list[str] = []
    product_type = "Skincare Product"
    top_confidence = 0.0
    skin_type_hint = None

    # ── detectLabels ────────────────────────────────────────────────────────
    try:
        label_resp = rek.detect_labels(
            Image={"S3Object": s3_obj},
            MaxLabels=10,
            MinConfidence=70,
        )
        labels = label_resp.get("Labels", [])
        detected_labels = [l["Name"] for l in labels[:5]]
        if labels:
            product_type = labels[0]["Name"]
            top_confidence = float(labels[0].get("Confidence", 0.0))
        logger.info(f"Rekognition detectLabels '{s3_key}': {detected_labels}")
    except Exception as e:
        logger.warning(f"Rekognition detectLabels failed for '{s3_key}': {e}")

    # ── detectText ──────────────────────────────────────────────────────────
    try:
        text_resp = rek.detect_text(Image={"S3Object": s3_obj})
        text_detections = text_resp.get("TextDetections", [])
        detected_words = " ".join(
            td["DetectedText"] for td in text_detections
            if td.get("Type") == "LINE"
        ).lower()

        for skin_type, keywords in SKIN_TYPE_KEYWORDS.items():
            for kw in keywords:
                if re.search(re.escape(kw), detected_words, re.IGNORECASE):
                    skin_type_hint = skin_type
                    logger.info(
                        f"Rekognition detectText '{s3_key}': skin_type_hint={skin_type} (keyword='{kw}')"
                    )
                    break
            if skin_type_hint:
                break
    except Exception as e:
        logger.warning(f"Rekognition detectText failed for '{s3_key}': {e}")

    return {
        "product_type": product_type,
        "detected_labels": detected_labels,
        "skin_type_hint": skin_type_hint,
        "top_confidence": top_confidence,
    }

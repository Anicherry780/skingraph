"""
Textract helpers for SkinGraph Phase 4.

Extracts the ingredient list from a product label photo already
uploaded to the skingraph-uploads S3 bucket.
"""

import logging
import os
import re

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)

UPLOADS_BUCKET = "skingraph-uploads"

# Lines that signal the start of an ingredient block
_INGREDIENT_HEADERS = re.compile(
    r"^(ingredients?|what.?s\s+inside|composition|inci\s+list|contains?|actives?)"
    r"[\s:]*$",
    re.IGNORECASE,
)

# Lines that signal the end of the ingredient block (next section)
_SECTION_BREAK = re.compile(
    r"^(directions?|how\s+to\s+use|usage|warnings?|caution|storage|shelf\s+life"
    r"|net\s+wt|weight|net\s+content|size|barcode|upc|batch|lot\s+no|mfg|mfd"
    r"|exp(iry|iration)?|best\s+before|made\s+in|distributed|manufactured)",
    re.IGNORECASE,
)


def _textract_client():
    return boto3.client(
        "textract",
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )


def extract_ingredients_from_s3(s3_key: str) -> dict:
    """
    Run Textract DETECT_DOCUMENT_TEXT on a photo in skingraph-uploads.

    Returns:
        {
            "ingredients_text": str,   # comma-joined ingredient lines
            "all_text":         str,   # full raw OCR text (space-joined)
            "found":            bool,  # True if ingredient section detected
        }
    """
    try:
        resp = _textract_client().detect_document_text(
            Document={
                "S3Object": {
                    "Bucket": UPLOADS_BUCKET,
                    "Name": s3_key,
                }
            }
        )
    except (BotoCoreError, ClientError) as e:
        logger.warning(f"Textract error for key '{s3_key}': {e}")
        return {"ingredients_text": "", "all_text": "", "found": False}
    except Exception as e:
        logger.warning(f"Textract unexpected error: {e}")
        return {"ingredients_text": "", "all_text": "", "found": False}

    # Collect LINE blocks in reading order
    lines = [
        b["Text"]
        for b in resp.get("Blocks", [])
        if b.get("BlockType") == "LINE"
    ]
    all_text = " ".join(lines)

    # Walk lines to find and capture the ingredients section
    capturing = False
    ingredient_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not capturing:
            if _INGREDIENT_HEADERS.match(stripped):
                capturing = True
            continue
        # Stop at next recognisable section header
        if _SECTION_BREAK.match(stripped):
            break
        ingredient_lines.append(stripped)

    ingredients_text = ", ".join(ingredient_lines)
    found = bool(ingredients_text)
    logger.info(
        f"Textract '{s3_key}': {len(lines)} lines → "
        f"ingredients found={found} ({len(ingredient_lines)} lines captured)"
    )

    return {
        "ingredients_text": ingredients_text,
        "all_text": all_text,
        "found": found,
    }

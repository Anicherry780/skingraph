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

# Header pattern — matches "Ingredients:", "Active Ingredients:", "Other Ingredients:"
# anywhere in a line (re.search, not re.match)
_INGREDIENT_HEADER = re.compile(
    r"(active\s+ingredients?|other\s+ingredients?|ingredients?)\s*:",
    re.IGNORECASE,
)

# Lines that signal the end of the ingredient block
_SECTION_BREAK = re.compile(
    r"(directions?|how\s+to\s+use|warnings?|caution|storage|for\s+all\s+types"
    r"|keep\s+out|patch\s+test|distributed|manufactured|net\s+wt|net\s+content)",
    re.IGNORECASE,
)

# Headers to skip when looking for product name
_NAME_SKIP_HEADER = re.compile(
    r"(ingredients?|active|other|directions?|warnings?|caution|storage)",
    re.IGNORECASE,
)


def _textract_client():
    return boto3.client(
        "textract",
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )


def _extract_product_name(lines: list[str]) -> str:
    """
    Best-guess product name from the first 10 lines of the label.
    Skips long lines, ingredient-heavy lines, and known section headers.
    Returns up to the first 1-2 short lines joined by a space.
    """
    candidates: list[str] = []
    for line in lines[:10]:
        stripped = line.strip()
        if not stripped:
            continue
        if len(stripped) > 60:
            continue
        if stripped.count(",") > 3:
            continue
        if _NAME_SKIP_HEADER.search(stripped):
            continue
        if _INGREDIENT_HEADER.search(stripped):
            continue
        candidates.append(stripped)
        if len(candidates) >= 2:
            break
    return " ".join(candidates)


def extract_all_from_s3(s3_key: str) -> dict:
    """
    Run Textract DETECT_DOCUMENT_TEXT on a photo in skingraph-uploads.

    Returns:
        {
            "ingredients_text": str,    # comma-joined ingredient lines
            "product_name_hint": str,   # from top label lines
            "all_text":         str,    # full raw OCR text (space-joined)
            "found":            bool,   # True if ingredient section detected
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
        return {"ingredients_text": "", "product_name_hint": "", "all_text": "", "found": False}
    except Exception as e:
        logger.warning(f"Textract unexpected error: {e}")
        return {"ingredients_text": "", "product_name_hint": "", "all_text": "", "found": False}

    # Collect LINE blocks in reading order
    lines = [
        b["Text"]
        for b in resp.get("Blocks", [])
        if b.get("BlockType") == "LINE"
    ]
    all_text = " ".join(lines)

    # Log every line with index for debugging
    logger.info(f"Textract '{s3_key}': {len(lines)} lines total")
    for i, line in enumerate(lines):
        logger.info(f"  [{i:02d}] {repr(line)}")

    # Extract product name from top of label
    product_name_hint = _extract_product_name(lines)
    logger.info(f"  product_name_hint: {repr(product_name_hint)}")

    # Walk lines to find and capture the ingredients section
    capturing = False
    ingredient_lines: list[str] = []

    for i, line in enumerate(lines):
        stripped = line.strip()

        if not capturing:
            m = _INGREDIENT_HEADER.search(stripped)
            if m:
                logger.info(f"  Header match at line [{i:02d}]: {repr(stripped)}")
                capturing = True
                # Capture everything after the colon on the same line
                after_colon = stripped[m.end():].strip()
                if after_colon:
                    logger.info(f"  Inline ingredients captured: {repr(after_colon)}")
                    ingredient_lines.append(after_colon)
            continue

        # Stop at next recognisable section header
        if _SECTION_BREAK.search(stripped):
            logger.info(f"  Section break at line [{i:02d}]: {repr(stripped)}")
            break

        logger.info(f"  Ingredient line [{i:02d}]: {repr(stripped)}")
        ingredient_lines.append(stripped)

    ingredients_text = ", ".join(ingredient_lines)
    found = bool(ingredients_text)
    logger.info(
        f"Textract '{s3_key}': ingredients found={found} ({len(ingredient_lines)} lines captured)"
    )

    return {
        "ingredients_text": ingredients_text,
        "product_name_hint": product_name_hint,
        "all_text": all_text,
        "found": found,
    }


# Backward-compat alias
extract_ingredients_from_s3 = extract_all_from_s3

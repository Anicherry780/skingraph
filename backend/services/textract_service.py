"""
Textract helpers for SkinGraph Phase 4.
Extracts ingredient list and product name from product label photos
already uploaded to the skingraph-uploads S3 bucket.
"""

import logging
import os
import re
from typing import Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)

UPLOADS_BUCKET = "skingraph-uploads"

# Header pattern — "Ingredients:", "Active Ingredients:", "Other Ingredients:"
_INGREDIENT_HEADER = re.compile(
    r"(active\s+ingredients?|other\s+ingredients?|inactive\s+ingredients?|ingredients?)\s*[:\.]",
    re.IGNORECASE,
)

# Lines that signal the END of the ingredient block
_SECTION_BREAK = re.compile(
    r"^(direction|how\s+to\s+use|warning|caution|storage|for\s+all\s+type|for\s+external"
    r"|keep\s+out|do\s+not|b\.?\s*no|batch|manufactured|distributed|net\s+wt|net\s+content"
    r"|patch\s+test|shelf\s+life)",
    re.IGNORECASE,
)

# Lines to skip when extracting product name
_NAME_SKIP = re.compile(
    r"(ingredients?|active|directions?|warnings?|caution|storage|how\s+to"
    r"|\b\d{4,}\b|\blot\b|\bexp\b|\bmfg\b|\bwww\.\|\.com)",
    re.IGNORECASE,
)


def _textract_client():
    return boto3.client(
        "textract",
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )


def _sort_blocks_by_position(blocks: list) -> list:
    """Sort LINE blocks top-to-bottom, left-to-right using BoundingBox."""
    def sort_key(b):
        geo = b.get("Geometry", {}).get("BoundingBox", {})
        top = geo.get("Top", 0)
        left = geo.get("Left", 0)
        # Bucket into rows by rounding Top to nearest 0.02 (≈ one line height)
        row = round(top / 0.02)
        return (row, left)
    return sorted(blocks, key=sort_key)


def _extract_product_name(lines: list[str]) -> str:
    """
    Best-guess product name from the first ~8 lines after sorting.
    Returns first 1-2 short meaningful lines joined by space.
    """
    candidates: list[str] = []
    for line in lines[:8]:
        stripped = line.strip()
        if not stripped:
            continue
        # Skip very short or very long lines
        if len(stripped) < 3 or len(stripped) > 60:
            continue
        # Skip lines with many commas (ingredient lists)
        if stripped.count(",") > 3:
            continue
        # Skip numbers-only, barcodes
        if re.match(r'^[\d\s\-\.]+$', stripped):
            continue
        # Skip known section headers
        if _NAME_SKIP.search(stripped):
            continue
        if _INGREDIENT_HEADER.search(stripped):
            continue
        candidates.append(stripped)
        if len(candidates) >= 2:
            break
    return " ".join(candidates)


def _parse_ingredients_from_lines(lines: list[str], s3_key: str = "") -> tuple[str, bool]:
    """
    Parse ingredient block from sorted lines.
    Returns (ingredients_text, found).
    """
    capturing = False
    ingredient_parts: list[str] = []

    for i, line in enumerate(lines):
        stripped = line.strip()

        if not capturing:
            m = _INGREDIENT_HEADER.search(stripped)
            if m:
                logger.info(f"  [{i:02d}] Header match: {repr(stripped)}")
                capturing = True
                # Grab anything after the colon/period on the same line
                after = stripped[m.end():].strip().rstrip(".")
                if after:
                    logger.info(f"  [{i:02d}] Inline ingredients: {repr(after)}")
                    ingredient_parts.append(after)
            else:
                logger.info(f"  [{i:02d}] (pre-header) {repr(stripped)}")
            continue

        # Check for section break
        if _SECTION_BREAK.search(stripped):
            logger.info(f"  [{i:02d}] Section break: {repr(stripped)}")
            break

        logger.info(f"  [{i:02d}] Ingredient line: {repr(stripped)}")
        ingredient_parts.append(stripped)

    combined = " ".join(ingredient_parts)
    # Clean up extra whitespace and trailing punctuation
    combined = re.sub(r"\s+", " ", combined).strip().rstrip(".")
    return combined, bool(combined)


def extract_all_from_s3(s3_key: str) -> dict:
    """
    Run Textract DETECT_DOCUMENT_TEXT on a photo in skingraph-uploads.
    Sorts blocks by Y position before parsing.

    Returns:
        {
            "ingredients_text": str,
            "product_name_hint": str,
            "all_text":         str,
            "found":            bool,
        }
    """
    try:
        resp = _textract_client().detect_document_text(
            Document={"S3Object": {"Bucket": UPLOADS_BUCKET, "Name": s3_key}}
        )
    except (BotoCoreError, ClientError) as e:
        logger.warning(f"Textract error for '{s3_key}': {e}")
        return {"ingredients_text": "", "product_name_hint": "", "all_text": "", "found": False}
    except Exception as e:
        logger.warning(f"Textract unexpected error: {e}")
        return {"ingredients_text": "", "product_name_hint": "", "all_text": "", "found": False}

    # Sort ALL LINE blocks by geometry before processing
    all_blocks = [b for b in resp.get("Blocks", []) if b.get("BlockType") == "LINE"]
    sorted_blocks = _sort_blocks_by_position(all_blocks)
    lines = [b["Text"] for b in sorted_blocks]

    logger.info(f"Textract '{s3_key}': {len(lines)} lines (sorted by Y position)")
    for i, line in enumerate(lines):
        geo = sorted_blocks[i].get("Geometry", {}).get("BoundingBox", {})
        logger.info(f"  [{i:02d}] Y={geo.get('Top', 0):.3f} {repr(line)}")

    all_text = " ".join(lines)
    product_name_hint = _extract_product_name(lines)
    logger.info(f"  product_name_hint: {repr(product_name_hint)}")

    ingredients_text, found = _parse_ingredients_from_lines(lines, s3_key)
    logger.info(f"  ingredients found={found}, length={len(ingredients_text)}")

    return {
        "ingredients_text": ingredients_text,
        "product_name_hint": product_name_hint,
        "all_text": all_text,
        "found": found,
    }


def merge_textract_results(results: list[dict]) -> dict:
    """
    Merge Textract results from multiple photos.
    - Combines ingredient lists, deduplicating individual ingredients
    - Takes product_name_hint from the result with the most text
    - Marks found=True if any result found ingredients
    """
    all_ingredient_parts: list[str] = []
    best_product_name = ""
    best_all_text_len = 0
    found = False

    for r in results:
        if r.get("found"):
            found = True
            text = r.get("ingredients_text", "")
            if text:
                all_ingredient_parts.append(text)
        # Pick product name from photo with most text (most legible)
        at_len = len(r.get("all_text", ""))
        if at_len > best_all_text_len and r.get("product_name_hint"):
            best_all_text_len = at_len
            best_product_name = r["product_name_hint"]

    # Deduplicate ingredients (split by comma, strip, lowercase compare)
    if all_ingredient_parts:
        seen: set[str] = set()
        unique: list[str] = []
        for part in all_ingredient_parts:
            for ing in re.split(r"[,،]", part):
                ing_stripped = ing.strip()
                ing_key = ing_stripped.lower()
                if ing_key and ing_key not in seen:
                    seen.add(ing_key)
                    unique.append(ing_stripped)
        merged_text = ", ".join(unique)
    else:
        merged_text = ""

    return {
        "ingredients_text": merged_text,
        "product_name_hint": best_product_name,
        "all_text": " | ".join(r.get("all_text", "") for r in results),
        "found": found,
    }


# Backward-compat alias
extract_ingredients_from_s3 = extract_all_from_s3

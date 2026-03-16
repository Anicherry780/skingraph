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

# Header pattern — colon/period is OPTIONAL (Textract often drops it)
# Matches: "Ingredients:", "Ingredients.", "Ingredients", "INGREDIENTS",
#          "Active Ingredients:", "Other Ingredients", etc.
_INGREDIENT_HEADER = re.compile(
    r"(active\s+ingredients?|other\s+ingredients?|inactive\s+ingredients?|ingredients?)"
    r"\s*[:\.\-]?\s*",
    re.IGNORECASE,
)

# Strict version: line IS the header (possibly with colon), nothing else meaningful
_INGREDIENT_HEADER_STANDALONE = re.compile(
    r"^\s*(active\s+ingredients?|other\s+ingredients?|inactive\s+ingredients?|ingredients?)"
    r"\s*[:\.\-]?\s*$",
    re.IGNORECASE,
)

# Lines that signal the END of the ingredient block
_SECTION_BREAK = re.compile(
    r"^(direction|how\s+to\s+use|warning|caution|storage|for\s+all\s+type|for\s+external"
    r"|keep\s+out|do\s+not|b\.?\s*no|batch|manufactured|distributed|net\s+wt|net\s+content"
    r"|patch\s+test|shelf\s+life|usage|apply|best\s+before|expiry|mfg|mfd)",
    re.IGNORECASE,
)

# Lines to skip when extracting product name
_NAME_SKIP = re.compile(
    r"(ingredients?|active|directions?|warnings?|caution|storage|how\s+to"
    r"|\b\d{4,}\b|\blot\b|\bexp\b|\bmfg\b|www\.|\.com)",
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
        if len(stripped) < 3 or len(stripped) > 60:
            continue
        if stripped.count(",") > 3:
            continue
        if re.match(r'^[\d\s\-\.]+$', stripped):
            continue
        if _NAME_SKIP.search(stripped):
            continue
        # Skip standalone ingredient headers
        if _INGREDIENT_HEADER_STANDALONE.match(stripped):
            continue
        candidates.append(stripped)
        if len(candidates) >= 2:
            break
    result = " ".join(candidates)
    logger.info(f"  _extract_product_name candidates={candidates} → {repr(result)}")
    return result


def _extract_from_all_text(all_text: str) -> tuple[str, bool]:
    """
    LAST-RESORT fallback: search the raw joined text for 'ingredient' keyword
    and extract everything between it and the next section-break keyword.
    Works even when Textract line splitting defeats line-based parsing.
    """
    if not all_text:
        return "", False

    # Find "ingredients" keyword (case-insensitive) in the full text
    lower = all_text.lower()
    idx = lower.find("ingredients")
    if idx == -1:
        # Also try without the 's'
        idx = lower.find("ingredient")
    if idx == -1:
        return "", False

    # Skip past the keyword and any colon/period
    after_keyword = all_text[idx:]
    m = _INGREDIENT_HEADER.match(after_keyword)
    if m:
        after_keyword = after_keyword[m.end():]
    else:
        # Skip "ingredients" or "ingredient" manually
        skip = len("ingredients") if lower[idx:idx+11] == "ingredients" else len("ingredient")
        after_keyword = all_text[idx + skip:]

    # Strip leading colon, period, dash, whitespace
    after_keyword = after_keyword.lstrip(":.- \t")

    # Find the end: look for section break keywords in the text
    section_break_in_text = re.compile(
        r"(?:for\s+all\s+type|for\s+external|keep\s+out|do\s+not|direction|"
        r"how\s+to\s+use|warning|caution|storage|manufactured|distributed|"
        r"batch|b\.?\s*no|net\s+wt|apply|best\s+before|expiry|mfg|mfd)",
        re.IGNORECASE,
    )
    end_match = section_break_in_text.search(after_keyword)
    if end_match:
        ingredients_raw = after_keyword[:end_match.start()]
    else:
        # Take up to 2000 chars max if no section break found
        ingredients_raw = after_keyword[:2000]

    # Clean up
    ingredients_raw = re.sub(r"\s+", " ", ingredients_raw).strip().rstrip(".")
    # Must have at least a few commas to be a real ingredient list
    if ingredients_raw.count(",") < 2:
        return "", False

    logger.info(f"  ALL_TEXT fallback: extracted {len(ingredients_raw)} chars, "
                f"{ingredients_raw.count(',') + 1} ingredients")
    logger.info(f"  ALL_TEXT preview: {ingredients_raw[:200]}")

    return ingredients_raw, True


def _parse_ingredients_from_lines(lines: list[str], s3_key: str = "") -> tuple[str, bool]:
    """
    Parse ingredient block from sorted lines.
    Strategy:
      1. Look for a line containing an ingredient header keyword
      2. If the header line also has text after the keyword → capture it (inline)
      3. If the header is standalone → capture all subsequent lines until section break
      4. FALLBACK 1: comma-heavy line block detection
      5. FALLBACK 2: search raw joined text for "ingredients" keyword
    Returns (ingredients_text, found).
    """
    capturing = False
    ingredient_parts: list[str] = []
    header_line_idx = -1

    for i, line in enumerate(lines):
        stripped = line.strip()

        if not capturing:
            # Check for standalone header first (e.g., "INGREDIENTS" alone on a line)
            if _INGREDIENT_HEADER_STANDALONE.match(stripped):
                logger.info(f"  PARSE [{i:02d}] ★ Standalone header: {repr(stripped)}")
                capturing = True
                header_line_idx = i
                continue

            # Check for inline header (e.g., "Ingredients: Water, Glycerin...")
            m = _INGREDIENT_HEADER.search(stripped)
            if m:
                capturing = True
                header_line_idx = i
                after = stripped[m.end():].strip().rstrip(".")
                if after and len(after) > 2:
                    logger.info(f"  PARSE [{i:02d}] ★ Inline header+ingredients: {repr(stripped)}")
                    logger.info(f"  PARSE [{i:02d}]   Captured after header: {repr(after)}")
                    ingredient_parts.append(after)
                else:
                    logger.info(f"  PARSE [{i:02d}] ★ Header (no inline): {repr(stripped)}")
                continue

            logger.info(f"  PARSE [{i:02d}] (skip) {repr(stripped)}")
            continue

        # We are capturing ingredients
        if _SECTION_BREAK.search(stripped):
            logger.info(f"  PARSE [{i:02d}] ■ Section break: {repr(stripped)}")
            break

        # Skip empty lines
        if not stripped:
            continue

        logger.info(f"  PARSE [{i:02d}] + Ingredient line: {repr(stripped)}")
        ingredient_parts.append(stripped)

    combined = " ".join(ingredient_parts)
    combined = re.sub(r"\s+", " ", combined).strip().rstrip(".")

    # ── FALLBACK 1: comma-heavy line detection ────────────────────────────
    if not combined:
        logger.info("  PARSE: header regex found nothing — trying comma-heavy fallback")
        comma_parts: list[str] = []
        in_comma_block = False

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            comma_count = stripped.count(",")

            # Start block with 1+ commas (lowered threshold from 2)
            if comma_count >= 1 and not in_comma_block:
                # Only start if total commas in this + next few lines suggest ingredient block
                # Look ahead: count total commas in next 3 lines
                lookahead_commas = comma_count
                for j in range(i + 1, min(i + 4, len(lines))):
                    lookahead_commas += lines[j].strip().count(",")
                if lookahead_commas >= 3:
                    in_comma_block = True
                    logger.info(f"  FALLBACK1 [{i:02d}] ★ Start (lookahead={lookahead_commas}): {repr(stripped)}")
                    comma_parts.append(stripped)
            elif in_comma_block and comma_count >= 1:
                logger.info(f"  FALLBACK1 [{i:02d}] + Continue: {repr(stripped)}")
                comma_parts.append(stripped)
            elif in_comma_block and comma_count == 0:
                # Check if this looks like a continuation (no period, short)
                if not _SECTION_BREAK.search(stripped) and len(stripped) < 60 and not stripped.endswith("."):
                    logger.info(f"  FALLBACK1 [{i:02d}] + Wrap line (no comma): {repr(stripped)}")
                    comma_parts.append(stripped)
                else:
                    logger.info(f"  FALLBACK1 [{i:02d}] ■ End block: {repr(stripped)}")
                    break

        if comma_parts:
            combined = " ".join(comma_parts)
            combined = re.sub(r"\s+", " ", combined).strip().rstrip(".")
            m2 = _INGREDIENT_HEADER.match(combined)
            if m2:
                combined = combined[m2.end():].strip()
            logger.info(f"  FALLBACK1 result: {len(comma_parts)} lines, {len(combined)} chars")

    # ── FALLBACK 2: raw all_text keyword search ───────────────────────────
    if not combined:
        logger.info("  PARSE: comma fallback found nothing — trying all_text keyword search")
        all_text = " ".join(lines)
        combined, _ = _extract_from_all_text(all_text)

    logger.info(
        f"  PARSE result: found={bool(combined)}, header_line={header_line_idx}, "
        f"parts={len(ingredient_parts)}, length={len(combined)}"
    )
    if combined:
        logger.info(f"  PARSE ingredients preview: {combined[:200]}{'...' if len(combined) > 200 else ''}")

    return combined, bool(combined)


def extract_all_from_s3(s3_key: str) -> dict:
    """
    Run Textract DETECT_DOCUMENT_TEXT on a photo in skingraph-uploads.
    Sorts blocks by Y position before parsing.
    """
    logger.info(f"TEXTRACT START: bucket={UPLOADS_BUCKET}, key={s3_key}")

    try:
        client = _textract_client()
        logger.info(f"TEXTRACT: calling detect_document_text(Bucket={UPLOADS_BUCKET}, Key={s3_key})")
        resp = client.detect_document_text(
            Document={"S3Object": {"Bucket": UPLOADS_BUCKET, "Name": s3_key}}
        )
        logger.info(f"TEXTRACT: API call succeeded")
    except (BotoCoreError, ClientError) as e:
        logger.error(f"TEXTRACT FAILED (boto error) for '{s3_key}': {e}")
        return {"ingredients_text": "", "product_name_hint": "", "all_text": "", "found": False}
    except Exception as e:
        logger.error(f"TEXTRACT FAILED (unexpected) for '{s3_key}': {e}")
        return {"ingredients_text": "", "product_name_hint": "", "all_text": "", "found": False}

    # Count all block types for diagnostics
    all_raw_blocks = resp.get("Blocks", [])
    block_types = {}
    for b in all_raw_blocks:
        bt = b.get("BlockType", "UNKNOWN")
        block_types[bt] = block_types.get(bt, 0) + 1
    logger.info(f"TEXTRACT raw response: {len(all_raw_blocks)} blocks, types={block_types}")

    # Filter LINE blocks and sort by Y position
    line_blocks = [b for b in all_raw_blocks if b.get("BlockType") == "LINE"]
    sorted_blocks = _sort_blocks_by_position(line_blocks)
    lines = [b["Text"] for b in sorted_blocks]

    logger.info(f"TEXTRACT '{s3_key}': {len(lines)} LINE blocks (sorted by Y)")
    logger.info("=" * 60)
    for i, line in enumerate(lines):
        geo = sorted_blocks[i].get("Geometry", {}).get("BoundingBox", {})
        y = geo.get("Top", 0)
        logger.info(f"  LINE [{i:02d}] Y={y:.3f} | {repr(line)}")
    logger.info("=" * 60)

    all_text = " ".join(lines)
    logger.info(f"TEXTRACT all_text ({len(all_text)} chars): {all_text[:300]}{'...' if len(all_text) > 300 else ''}")

    product_name_hint = _extract_product_name(lines)
    logger.info(f"TEXTRACT product_name_hint: {repr(product_name_hint)}")

    ingredients_text, found = _parse_ingredients_from_lines(lines, s3_key)
    logger.info(f"TEXTRACT FINAL: found={found}, ingredients_len={len(ingredients_text)}")
    if found:
        logger.info(f"TEXTRACT ingredients: {ingredients_text[:300]}")
    else:
        logger.warning(f"TEXTRACT: NO INGREDIENTS FOUND in {len(lines)} lines from {s3_key}")

    return {
        "ingredients_text": ingredients_text,
        "product_name_hint": product_name_hint,
        "all_text": all_text,
        "found": found,
    }


def merge_textract_results(results: list[dict]) -> dict:
    """
    Merge Textract results from multiple photos.
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
        at_len = len(r.get("all_text", ""))
        if at_len > best_all_text_len and r.get("product_name_hint"):
            best_all_text_len = at_len
            best_product_name = r["product_name_hint"]

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

    logger.info(
        f"MERGE: {len(results)} photos → found={found}, "
        f"ingredients_len={len(merged_text)}, product_name={repr(best_product_name)}"
    )

    return {
        "ingredients_text": merged_text,
        "product_name_hint": best_product_name,
        "all_text": " | ".join(r.get("all_text", "") for r in results),
        "found": found,
    }


# Backward-compat alias
extract_ingredients_from_s3 = extract_all_from_s3

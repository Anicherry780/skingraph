"""
POST /api/alternatives

Uses Nova 2 Lite to suggest 3 real, cheaper alternatives with similar active ingredients.
No product database needed — Nova knows skincare products from training data.
Match percentages use recall-based formula (shared / original product ingredients),
answering "how much of your product's formula does this alternative cover?"
"""

import json
import logging
import math
import os
from typing import List, Optional
from urllib.parse import quote_plus

import boto3
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

NOVA_LITE_MODEL_ID = "amazon.nova-lite-v1:0"


# ── Request model ─────────────────────────────────────────────────────────────

class AlternativesRequest(BaseModel):
    product_name: str
    skin_type: str
    key_ingredients: List[str] = []
    estimated_price: Optional[str] = None


# ── Ingredient match calculation ─────────────────────────────────────────────

def _normalize_ingredient(name: str) -> str:
    """Lowercase, strip whitespace, remove common suffixes for matching."""
    return name.lower().strip().rstrip(".,;")


def _calculate_match(original_ingredients: List[str], alt_ingredients: List[str]) -> dict:
    """
    Calculate real ingredient overlap using recall-based formula:
    match % = (shared ingredients / original product ingredients) × 100

    This answers: "How much of MY product's formula does this alternative cover?"
    More intuitive than Jaccard for consumer-facing skincare comparison.

    Returns {"match_percent": int, "shared_count": int, "has_ingredients": bool}
    """
    if not alt_ingredients or not original_ingredients:
        return {"match_percent": 0, "shared_count": 0, "has_ingredients": False}

    orig_set = {_normalize_ingredient(i) for i in original_ingredients if i.strip()}
    alt_set = {_normalize_ingredient(i) for i in alt_ingredients if i.strip()}

    if not orig_set or not alt_set:
        return {"match_percent": 0, "shared_count": 0, "has_ingredients": False}

    shared = orig_set & alt_set
    raw_pct = (len(shared) / len(orig_set)) * 100 if len(orig_set) > 0 else 0

    # Round to nearest 5%
    match_pct = int(5 * round(raw_pct / 5))
    match_pct = max(0, min(100, match_pct))

    return {
        "match_percent": match_pct,
        "shared_count": len(shared),
        "has_ingredients": True,
    }


# ── Nova 2 Lite alternatives finder ──────────────────────────────────────────

def _find_alternatives_via_nova(
    product_name: str,
    skin_type: str,
    key_ingredients: List[str],
) -> List[dict]:
    try:
        client = boto3.client(
            "bedrock-runtime",
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )

        ingredients_str = ", ".join(key_ingredients[:15]) if key_ingredients else "not specified"

        prompt = f"""You are a skincare product expert with deep knowledge of the global skincare market.

Product to find alternatives for: {product_name}
Skin type: {skin_type}
Key active ingredients: {ingredients_str}

Suggest exactly 3 real, widely available alternative skincare products with overlapping active ingredients.
Only suggest products that genuinely exist and are sold on major retailers.

Return ONLY a valid JSON object — no markdown, no explanation, nothing else:
{{
  "alternatives": [
    {{
      "name": "Full Product Name",
      "brand": "Brand Name",
      "key_matching_ingredients": ["ingredient1", "ingredient2", "ingredient3"],
      "why_similar": "One sentence: which active ingredients overlap and why it works for {skin_type} skin"
    }}
  ]
}}

Rules:
- All 3 products must genuinely exist
- Prefer well-known brands: The Ordinary, CeraVe, Neutrogena, Vanicream, Cetaphil, La Roche-Posay, Eucerin, Paula's Choice, Cosrx
- key_matching_ingredients must list ONLY ingredients that are ACTUALLY in both the original and the alternative
- Do NOT include prices — we will link to Amazon for real pricing
- All alternatives must suit {skin_type} skin
- Return ONLY the JSON object"""

        body = {
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "inferenceConfig": {"maxTokens": 1024, "temperature": 0.2},
        }

        response = client.invoke_model(
            modelId=NOVA_LITE_MODEL_ID,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )

        response_body = json.loads(response["body"].read())
        raw = response_body["output"]["message"]["content"][0]["text"].strip()

        # Strip markdown code fences if Nova added them
        if raw.startswith("```"):
            lines = raw.split("\n")
            lines = lines[1:] if lines[0].startswith("```") else lines
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            raw = "\n".join(lines).strip()

        data = json.loads(raw)
        alternatives = data.get("alternatives", [])

        # Calculate real match % and attach Amazon URL
        for alt in alternatives:
            # Real ingredient overlap calculation
            alt_ingredients = alt.get("key_matching_ingredients", [])
            match_info = _calculate_match(key_ingredients, alt_ingredients)
            alt["match_percent"] = match_info["match_percent"]
            alt["shared_count"] = match_info["shared_count"]
            alt["has_ingredients"] = match_info["has_ingredients"]

            # Remove any fake price Nova might have generated
            alt.pop("estimated_price", None)
            alt.pop("price", None)

            # Amazon search URL
            query = quote_plus(alt.get("name", product_name))
            alt["amazon_url"] = f"https://www.amazon.com/s?k={query}"

        logger.info(f"Found {len(alternatives)} alternatives for: {product_name}")
        return alternatives

    except json.JSONDecodeError as e:
        logger.error(f"Alternatives JSON parse error: {e}")
        return []
    except Exception as e:
        logger.error(f"Alternatives Nova error: {e}", exc_info=True)
        return []


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/api/alternatives")
async def get_alternatives(req: AlternativesRequest):
    logger.info(f"Alternatives request: {req.product_name} / {req.skin_type}")
    try:
        alternatives = _find_alternatives_via_nova(
            product_name=req.product_name,
            skin_type=req.skin_type,
            key_ingredients=req.key_ingredients,
        )
        return {
            "product_name": req.product_name,
            "skin_type": req.skin_type,
            "alternatives": alternatives,
        }
    except Exception as e:
        logger.error(f"Alternatives endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Could not fetch alternatives.")

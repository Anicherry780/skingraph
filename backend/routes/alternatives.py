"""
POST /api/alternatives

Uses Nova 2 Lite to suggest 3 real, cheaper alternatives with similar active ingredients.
No product database needed — Nova knows skincare products from training data.
"""

import json
import logging
import os
from typing import List, Optional

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


# ── Nova 2 Lite alternatives finder ──────────────────────────────────────────

def _find_alternatives_via_nova(
    product_name: str,
    skin_type: str,
    key_ingredients: List[str],
    estimated_price: Optional[str],
) -> List[dict]:
    try:
        client = boto3.client(
            "bedrock-runtime",
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )

        ingredients_str = ", ".join(key_ingredients[:15]) if key_ingredients else "not specified"
        price_note = (
            f"Current retail price: {estimated_price}. Prioritize cheaper options."
            if estimated_price
            else "Find affordable, budget-friendly options under $25."
        )

        prompt = f"""You are a skincare product expert with deep knowledge of the global skincare market.

Product to find alternatives for: {product_name}
Skin type: {skin_type}
Key active ingredients: {ingredients_str}
{price_note}

Suggest exactly 3 real, widely available cheaper alternative skincare products with overlapping active ingredients.
Only suggest products that genuinely exist and are sold on Amazon.

Return ONLY a valid JSON object — no markdown, no explanation, nothing else:
{{
  "alternatives": [
    {{
      "name": "Full Product Name",
      "brand": "Brand Name",
      "estimated_price": "$X.XX",
      "match_percent": <integer 70-95>,
      "key_matching_ingredients": ["ingredient1", "ingredient2", "ingredient3"],
      "why_similar": "One sentence: which active ingredients overlap and why it works for {skin_type} skin"
    }}
  ]
}}

Rules:
- All 3 products must genuinely exist and be available on Amazon
- Prefer well-known brands: The Ordinary, CeraVe, Neutrogena, Vanicream, Cetaphil, La Roche-Posay, Eucerin, Paula's Choice, Cosrx
- match_percent reflects active ingredient overlap (70–95 is realistic)
- estimated_price must be a realistic retail price lower than or comparable to the original
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

        # Attach Amazon search URL to each alternative
        for alt in alternatives:
            query = alt.get("name", product_name).replace(" ", "+")
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
            estimated_price=req.estimated_price,
        )
        return {
            "product_name": req.product_name,
            "skin_type": req.skin_type,
            "alternatives": alternatives,
        }
    except Exception as e:
        logger.error(f"Alternatives endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Could not fetch alternatives.")

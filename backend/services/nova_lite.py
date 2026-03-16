"""
Nova 2 Lite ingredient analysis via Amazon Bedrock.
Model: amazon.nova-lite-v1:0
Returns structured suitability score, ingredient breakdown, red flags, reality check.
"""

import json
import logging
import os
from typing import Optional

import boto3

logger = logging.getLogger(__name__)

NOVA_LITE_MODEL_ID = "amazon.nova-lite-v1:0"


def _bedrock_client():
    return boto3.client(
        "bedrock-runtime",
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )


def _strip_markdown(text: str) -> str:
    """Remove markdown code fences that Nova might add."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Drop first line (```json or ```) and last (```)
        lines = lines[1:] if lines[0].startswith("```") else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _build_prompt(
    product_name: str,
    skin_type: str,
    ingredients_text: str,
    brand_claims: Optional[str],
) -> str:
    claims_section = f"\nBrand claims: {brand_claims}" if brand_claims else ""

    return f"""You are SkinGraph, an expert cosmetic chemist and skincare analyst trusted by dermatologists.

Product: {product_name}
Target skin type: {skin_type}
Ingredients list: {ingredients_text}{claims_section}

Analyze these ingredients for someone with {skin_type} skin. Return ONLY a valid JSON object — no markdown, no explanation, no extra text — with this exact structure:

{{
  "suitability_score": <integer 0-100>,
  "summary": "<2-sentence summary of overall suitability for {skin_type} skin>",
  "ingredients": [
    {{
      "name": "<ingredient name>",
      "category": "<one of: moisturizer|exfoliant|preservative|fragrance|active|emollient|occlusive|humectant|antioxidant|surfactant|other>",
      "is_flagged": <true or false>,
      "flag_reason": "<concise reason if flagged, otherwise null>",
      "description": "<1-sentence benefit or function>",
      "irritant_risk": "<none|low|medium|high>",
      "comedogenic_rating": <integer 0-5>,
      "safe_for_skin_type": "<safe|caution|avoid> for {skin_type} skin — return only the word: safe, caution, or avoid"
    }}
  ],
  "red_flags": [
    {{
      "ingredient": "<ingredient name>",
      "reason": "<why it is problematic for {skin_type} skin>",
      "severity": "<low|medium|high>"
    }}
  ],
  "reality_check": "<2-3 sentences comparing brand claims to what the ingredient list actually delivers>"
}}

Scoring guide:
- 80-100: Excellent match — key actives align well with {skin_type} skin needs
- 60-79: Good with minor concerns
- 40-59: Mixed — some beneficial ingredients, some concerns
- 0-39: Problematic — multiple ingredients that worsen {skin_type} skin

Rules:
- List ALL ingredients from the ingredient list — do not truncate or limit the count
- Flag ingredients that are irritating, comedogenic, or counterproductive for {skin_type} skin
- If ingredient list is unavailable, return score 50 and note it in summary
- Be evidence-based. Avoid marketing language.
- Return ONLY the JSON object. No other text whatsoever."""


def analyze_ingredients(
    product_name: str,
    skin_type: str,
    ingredients_text: str,
    brand_claims: Optional[str] = None,
) -> dict:
    """
    Call Nova 2 Lite on Bedrock to analyze ingredients.
    Falls back to _fallback_analysis if Bedrock is unavailable.
    """
    prompt = _build_prompt(product_name, skin_type, ingredients_text, brand_claims)

    try:
        client = _bedrock_client()

        body = {
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "inferenceConfig": {
                "maxTokens": 4096,
                "temperature": 0.1,
            },
        }

        response = client.invoke_model(
            modelId=NOVA_LITE_MODEL_ID,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )

        response_body = json.loads(response["body"].read())
        raw_text = response_body["output"]["message"]["content"][0]["text"]
        clean_text = _strip_markdown(raw_text)

        analysis = json.loads(clean_text)
        logger.info(
            f"Nova Lite analysis complete — score: {analysis.get('suitability_score')}"
        )
        return analysis

    except json.JSONDecodeError as e:
        raw_preview = raw_text[:200] if 'raw_text' in dir() else "(no response)"
        logger.error(f"Nova Lite JSON parse failed: {e} | raw: {raw_preview}")
        return _fallback_analysis(product_name, skin_type)
    except Exception as e:
        if "AccessDeniedException" in str(type(e).__name__) or "AccessDenied" in str(e):
            logger.error("Bedrock access denied — check IAM permissions and model access")
            return _fallback_analysis(product_name, skin_type, error="bedrock_access_denied")
    except Exception as e:
        logger.error(f"Nova Lite error: {e}", exc_info=True)
        return _fallback_analysis(product_name, skin_type)


def _levenshtein(a: str, b: str) -> int:
    """Simple Levenshtein distance."""
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (ca != cb)))
        prev = curr
    return prev[-1]


def correct_product_name(product_name: str) -> str:
    """
    Use Nova 2 Lite to fix obvious typos in skincare product names.
    Conservative: rejects correction if it changes >40% of characters.
    """
    if len(product_name.strip()) <= 3:
        return product_name

    prompt = (
        "Fix ONLY spelling typos in this skincare product name. "
        "Do NOT change the brand name. Do NOT replace it with a different brand. "
        "Do NOT add new words. If it looks like an unknown or foreign brand name, "
        "return it exactly as typed. Only fix obvious character-level typos "
        "like 'creem' → 'cream' or 'moisterizer' → 'moisturizer'. "
        "Return only the corrected name, nothing else.\n\n"
        f"Product name: {product_name}"
    )
    try:
        client = _bedrock_client()
        body = {
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "inferenceConfig": {"maxTokens": 60, "temperature": 0.1},
        }
        resp = client.invoke_model(
            modelId=NOVA_LITE_MODEL_ID,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )
        rb = json.loads(resp["body"].read())
        corrected = rb["output"]["message"]["content"][0]["text"].strip().strip('"\'')

        if not corrected:
            return product_name

        # Reject if correction changes more than 40% of characters (too aggressive)
        max_len = max(len(product_name), len(corrected), 1)
        dist = _levenshtein(product_name.lower(), corrected.lower())
        if dist / max_len > 0.40:
            logger.info(
                f"Spell correction rejected (distance {dist}/{max_len}={dist/max_len:.0%}): "
                f"'{product_name}' → '{corrected}'"
            )
            return product_name

        logger.info(f"Spell correction: '{product_name}' → '{corrected}'")
        return corrected
    except Exception as e:
        logger.warning(f"Spell correction failed: {e}")
        return product_name


def research_product_ingredients(product_name: str) -> dict:
    """
    Multi-tier ingredient research when Textract and OBF exact search both failed.

    Tier 1: OBF broader search — try name variations
    Tier 2: Nova 2 Lite knowledge estimate — formulate based on product type

    Returns {"ingredients_text": str, "found": bool, "source": str}
    source is "obf_research" | "estimated" | "not_found"
    """
    import re as _re
    import requests as _requests

    # ── Tier 1: OBF broader search with name variations ──────────────────
    logger.info(f"Research Tier 1: OBF broader search for '{product_name}'")

    # Extract product type from parenthetical if present, e.g. "la screen (Sunscreen, SPF 50+)"
    paren_match = _re.search(r"\(([^)]+)\)", product_name)
    base_name = _re.sub(r"\s*\([^)]*\)\s*", " ", product_name).strip()
    product_type = ""
    product_detail = ""
    if paren_match:
        paren_parts = [p.strip() for p in paren_match.group(1).split(",")]
        product_type = paren_parts[0] if paren_parts else ""
        product_detail = paren_parts[1] if len(paren_parts) > 1 else ""

    # Build search variations
    search_variations = [
        base_name,                                               # "la screen ultra"
        f"{base_name} {product_type}".strip(),                   # "la screen ultra Sunscreen"
    ]
    # Add just brand words (first 1-2 words)
    words = base_name.split()
    if len(words) >= 2:
        search_variations.append(" ".join(words[:2]))            # "la screen"
    # Add product type alone if it's specific enough
    if product_type and product_detail:
        search_variations.append(f"{product_type} {product_detail}")  # "Sunscreen SPF 50+"

    OBF_SEARCH_URL = "https://world.openbeautyfacts.org/cgi/search.pl"

    for variation in search_variations:
        if not variation or len(variation) < 3:
            continue
        try:
            logger.info(f"Research OBF search: '{variation}'")
            params = {
                "search_terms": variation,
                "search_simple": 1,
                "action": "process",
                "json": 1,
                "page_size": 5,
                "fields": "product_name,ingredients_text,brands",
            }
            resp = _requests.get(OBF_SEARCH_URL, params=params, timeout=8)
            resp.raise_for_status()
            data = resp.json()
            products = data.get("products", [])

            for p in products:
                ing_text = (p.get("ingredients_text") or "").strip()
                if ing_text and len(ing_text) > 20:
                    # Clean up
                    ing_text = _re.sub(r"\*+[^,]*", "", ing_text)
                    ing_text = _re.sub(r"\[\d+\]", "", ing_text)
                    ing_text = _re.sub(r"\s+", " ", ing_text).strip().rstrip("., ")
                    obf_name = p.get("product_name") or variation
                    logger.info(f"Research OBF HIT via '{variation}': "
                                f"product='{obf_name}', ingredients_len={len(ing_text)}")
                    return {
                        "ingredients_text": ing_text,
                        "found": True,
                        "source": "obf_research",
                    }

            logger.info(f"Research OBF '{variation}': no ingredients in {len(products)} results")
        except Exception as e:
            logger.warning(f"Research OBF search failed for '{variation}': {e}")

    # ── Tier 2: Nova 2 Lite knowledge-based estimation ───────────────────
    logger.info(f"Research Tier 2: Nova estimate for '{product_name}'")

    type_hint = product_type or "skincare product"
    detail_hint = f" with {product_detail}" if product_detail else ""

    prompt = (
        "You are a cosmetic chemist with deep knowledge of skincare formulations.\n\n"
        f"Product: {product_name}\n"
        f"Product type: {type_hint}{detail_hint}\n\n"
        "Based on your knowledge of typical formulations for this type of product, "
        "list the most likely ingredients in INCI format, as they would appear on a real label. "
        "Include 12-18 ingredients typical for this product type. "
        "Start with the base (like Water/Aqua), then key actives, then common "
        "emollients, preservatives, and other standard ingredients.\n\n"
        "Return ONLY the comma-separated ingredient list, nothing else. "
        "If you truly cannot determine any likely ingredients, return exactly: UNKNOWN"
    )
    try:
        client = _bedrock_client()
        body = {
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "inferenceConfig": {"maxTokens": 512, "temperature": 0.2},
        }
        resp = client.invoke_model(
            modelId=NOVA_LITE_MODEL_ID,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )
        rb = json.loads(resp["body"].read())
        text = rb["output"]["message"]["content"][0]["text"].strip()

        # Strip markdown fences if present
        text = _strip_markdown(text)

        if not text or "UNKNOWN" in text.upper() or len(text) < 15:
            logger.info(f"Research estimate: Nova returned no usable ingredients for '{product_name}'")
            return {"ingredients_text": "", "found": False, "source": "not_found"}

        # Validate: should look like a comma-separated list
        commas = text.count(",")
        if commas < 3:
            logger.info(f"Research estimate: too few commas ({commas}), likely not an ingredient list")
            return {"ingredients_text": "", "found": False, "source": "not_found"}

        logger.info(f"Research estimate SUCCESS for '{product_name}': {text[:200]}")
        return {"ingredients_text": text, "found": True, "source": "estimated"}
    except Exception as e:
        logger.warning(f"Research estimate failed for '{product_name}': {e}")
        return {"ingredients_text": "", "found": False, "source": "not_found"}


def _fallback_analysis(
    product_name: str, skin_type: str, error: str = "unavailable"
) -> dict:
    """Minimal valid response when Bedrock is unreachable."""
    return {
        "suitability_score": 50,
        "summary": (
            f"Full AI analysis for {product_name} is temporarily unavailable. "
            "Please try again in a moment."
        ),
        "ingredients": [],
        "red_flags": [],
        "reality_check": "AI analysis temporarily unavailable.",
        "error": error,
    }

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
- List the top 12 most important or interesting ingredients only
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
                "maxTokens": 2048,
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
        logger.error(f"Nova Lite JSON parse failed: {e} | raw: {raw_text[:200]}")
        return _fallback_analysis(product_name, skin_type)
    except client.exceptions.AccessDeniedException:
        logger.error("Bedrock access denied — check IAM permissions and model access")
        return _fallback_analysis(product_name, skin_type, error="bedrock_access_denied")
    except Exception as e:
        logger.error(f"Nova Lite error: {e}", exc_info=True)
        return _fallback_analysis(product_name, skin_type)


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

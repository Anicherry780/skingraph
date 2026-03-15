"""
POST /api/analyze — main analysis endpoint.

Pipeline:
1. Resolve skin type (backend inference if "auto")
2. Generate embedding for cache lookup
3. Check Supabase cache (vector similarity first, hash fallback)
4. Fetch ingredients from Open Beauty Facts (free, no API key)
5. Run Nova Act: brand site claims only (1 session)
6. Analyze ingredients with Nova 2 Lite on Bedrock
7. Save result + embedding to cache
8. Return full analysis
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from services.nova_embeddings import check_cache, generate_embedding, save_to_cache
from services.nova_lite import analyze_ingredients
from services.open_beauty_facts import fetch_ingredients
from services.lambda_trigger import run_nova_act_parallel
from services.skin_type_inference import infer_skin_type

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request model ────────────────────────────────────────────────────────────

VALID_SKIN_TYPES = {"oily", "dry", "combination", "sensitive", "auto"}


class AnalyzeRequest(BaseModel):
    product_name: str
    skin_type: str = "auto"
    skin_type_inferred: bool = False
    second_product: Optional[str] = None
    image_base64: Optional[str] = None

    @field_validator("product_name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("product_name must not be empty")
        return v

    @field_validator("skin_type")
    @classmethod
    def valid_skin_type(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in VALID_SKIN_TYPES:
            raise ValueError(f"skin_type must be one of {VALID_SKIN_TYPES}")
        return v


# ── Endpoint ─────────────────────────────────────────────────────────────────

@router.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    logger.info(f"Analyze: '{req.product_name}' skin_type={req.skin_type}")

    try:
        # ── 1. Resolve skin type ─────────────────────────────────────────────
        skin_type = req.skin_type
        skin_type_inferred = req.skin_type_inferred

        if skin_type == "auto":
            inferred, was_inferred, reason = infer_skin_type(req.product_name)
            skin_type = inferred or "combination"
            skin_type_inferred = was_inferred
            logger.info(f"Skin type resolved: {skin_type} (inferred={was_inferred})")

        # ── 2. Generate embedding (used for cache lookup + storage) ──────────
        embed_text = f"{req.product_name} {skin_type}"
        embedding = generate_embedding(embed_text)

        # ── 3. Cache check (vector similarity → hash fallback) ───────────────
        cached = check_cache(req.product_name, skin_type, embedding=embedding)
        if cached:
            return {
                **cached,
                "product_name": req.product_name,
                "skin_type": skin_type,
                "skin_type_inferred": skin_type_inferred,
            }

        # ── 4. Open Beauty Facts ─────────────────────────────────────────────
        obf = fetch_ingredients(req.product_name)
        ingredients_text = obf.get("ingredients_text") or ""
        ingredients_found = obf.get("found", False)
        logger.info(f"OBF ingredients found: {ingredients_found}")

        if not ingredients_text:
            ingredients_text = "Ingredient list not available in Open Beauty Facts database."

        # ── 5. Nova Act: brand claims only (1 session) ───────────────────────
        nova_result = run_nova_act_parallel(req.product_name)
        brand_claims = nova_result.get("brand_claims")

        # ── 6. Nova 2 Lite ingredient analysis ───────────────────────────────
        analysis = analyze_ingredients(
            product_name=req.product_name,
            skin_type=skin_type,
            ingredients_text=ingredients_text,
            brand_claims=brand_claims,
        )

        # ── 7. Build response ────────────────────────────────────────────────
        result = {
            **analysis,
            "product_name": req.product_name,
            "skin_type": skin_type,
            "skin_type_inferred": skin_type_inferred,
            "brand_claims": brand_claims,
            "amazon_price": None,       # Phase 3: restore via alternatives endpoint
            "ingredients_found": ingredients_found,
            "cached": False,
        }

        # ── 8. Save to cache with embedding ──────────────────────────────────
        save_to_cache(req.product_name, skin_type, analysis, embedding=embedding)

        return result

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Analyze error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Analysis failed. Please try again.")

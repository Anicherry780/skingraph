"""
POST /api/analyze — main analysis endpoint.

Pipeline (no image):
1. Resolve skin type (backend inference if "auto")
2. Generate embedding for cache lookup
3. Check Supabase cache (vector similarity first, hash fallback)
4. Fetch ingredients from Open Beauty Facts (free, no API key)
5. Run Nova Act: brand site claims only (1 session)
6. Analyze ingredients with Nova 2 Lite on Bedrock
7. Save result + embedding to Supabase; persist JSON to S3
8. Return full analysis

Pipeline (with image_base64 — Phase 4):
1. Resolve skin type
2. Upload photo to S3 (skingraph-uploads, auto-deleted after 1 day)
3. Run Textract to extract ingredient list from label
4. Skip Open Beauty Facts — use Textract text directly
5. Run Nova Act: brand claims
6. Analyze with Nova 2 Lite
7. Save to Supabase cache + S3 analyses bucket
8. Return full analysis
"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from services.nova_embeddings import check_cache, generate_embedding, save_to_cache
from services.nova_lite import analyze_ingredients, correct_product_name
from services.open_beauty_facts import fetch_ingredients
from services.lambda_trigger import run_nova_act_parallel
from services.skin_type_inference import infer_skin_type
from services.s3_service import upload_photo, save_analysis
from services.textract_service import extract_all_from_s3

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
    logger.info(
        f"Analyze: '{req.product_name}' skin_type={req.skin_type} "
        f"has_image={bool(req.image_base64)}"
    )

    try:
        # ── 1. Resolve skin type ─────────────────────────────────────────────
        skin_type = req.skin_type
        skin_type_inferred = req.skin_type_inferred

        if skin_type == "auto":
            inferred, was_inferred, reason = infer_skin_type(req.product_name)
            skin_type = inferred or "combination"
            skin_type_inferred = was_inferred
            logger.info(f"Skin type resolved: {skin_type} (inferred={was_inferred})")

        # ── 1b. Spell correction ─────────────────────────────────────────────
        corrected_name = correct_product_name(req.product_name)
        name_was_corrected = corrected_name.lower() != req.product_name.lower()
        display_name = corrected_name if name_was_corrected else req.product_name
        logger.info(f"Using name: '{display_name}' (corrected={name_was_corrected})")

        # ── 2. Generate embedding (used for cache lookup + storage) ──────────
        embed_text = f"{display_name} {skin_type}"
        embedding = generate_embedding(embed_text)

        # ── 3. Cache check (vector similarity → hash fallback) ───────────────
        cached = check_cache(display_name, skin_type, embedding=embedding)
        if cached:
            return {
                **cached,
                "product_name": display_name,
                "skin_type": skin_type,
                "skin_type_inferred": skin_type_inferred,
                "corrected_name": corrected_name if name_was_corrected else None,
            }

        # ── 4. Ingredient source: Textract (image) or Open Beauty Facts ──────
        ingredients_text = ""
        ingredients_found = False

        if req.image_base64:
            logger.info("Phase 4: uploading label photo to S3 → Textract")
            s3_key = upload_photo(req.image_base64, f"{uuid.uuid4().hex}.jpg")

            if s3_key:
                textract = extract_all_from_s3(s3_key)
                ingredients_text = textract.get("ingredients_text", "")
                ingredients_found = textract.get("found", False)
                if ingredients_found:
                    logger.info("Textract: ingredients extracted from label")
                else:
                    logger.info("Textract: no ingredients found — falling back to OBF")
            else:
                logger.warning("S3 upload failed — using OBF fallback")

            # Fall back to OBF if Textract came up empty
            if not ingredients_text:
                obf = fetch_ingredients(display_name)
                ingredients_text = obf.get("ingredients_text") or ""
                ingredients_found = obf.get("found", False)
        else:
            # Standard path: Open Beauty Facts
            obf = fetch_ingredients(display_name)
            ingredients_text = obf.get("ingredients_text") or ""
            ingredients_found = obf.get("found", False)
            logger.info(f"OBF ingredients found: {ingredients_found}")

        if not ingredients_text:
            ingredients_text = "Ingredient list not available."

        # ── 5. Nova Act: brand claims only (1 session) ───────────────────────
        nova_result = run_nova_act_parallel(display_name)
        brand_claims = nova_result.get("brand_claims")

        # ── 6. Nova 2 Lite ingredient analysis ───────────────────────────────
        analysis = analyze_ingredients(
            product_name=display_name,
            skin_type=skin_type,
            ingredients_text=ingredients_text,
            brand_claims=brand_claims,
        )

        # ── 7. Build response ────────────────────────────────────────────────
        result = {
            **analysis,
            "product_name": display_name,
            "skin_type": skin_type,
            "skin_type_inferred": skin_type_inferred,
            "brand_claims": brand_claims,
            "amazon_price": None,
            "ingredients_found": ingredients_found,
            "cached": False,
            "corrected_name": corrected_name if name_was_corrected else None,
        }

        # ── 8. Save to Supabase cache + S3 analyses bucket ───────────────────
        save_to_cache(display_name, skin_type, analysis, embedding=embedding)
        save_analysis(display_name, skin_type, result)

        return result

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Analyze error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Analysis failed. Please try again.")

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
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from services.nova_embeddings import check_cache, generate_embedding, save_to_cache
from services.nova_lite import analyze_ingredients, correct_product_name, research_product_ingredients
from services.open_beauty_facts import fetch_ingredients
from services.lambda_trigger import run_nova_act_parallel
from services.skin_type_inference import infer_skin_type
from services.s3_service import upload_photo, save_analysis
from services.textract_service import extract_all_from_s3, merge_textract_results

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
    images_base64: list[str] = []

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

    @field_validator("images_base64")
    @classmethod
    def check_images_max(cls, v: list[str]) -> list[str]:
        if len(v) > 5:
            raise ValueError("Maximum 5 images allowed")
        return v

    def get_all_images(self) -> list[str]:
        """Unified list of base64 images (new list + backward-compat single)."""
        imgs = list(self.images_base64)
        if self.image_base64 and self.image_base64 not in imgs:
            imgs.append(self.image_base64)
        return imgs[:5]


# ── Endpoint ─────────────────────────────────────────────────────────────────

@router.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    logger.info(
        f"Analyze: '{req.product_name}' skin_type={req.skin_type} "
        f"has_images={len(req.get_all_images())}"
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
        ingredient_source = "not_found"

        all_images = req.get_all_images()
        logger.info(f"ANALYZE images: count={len(all_images)}, "
                     f"images_base64_len={len(req.images_base64)}, "
                     f"image_base64_present={req.image_base64 is not None}")

        if all_images:
            logger.info(f"ANALYZE Phase 4: processing {len(all_images)} image(s), "
                         f"sizes={[len(img) for img in all_images]} chars base64")

            def _process_image(b64: str, idx: int) -> dict:
                logger.info(f"ANALYZE _process_image[{idx}]: uploading {len(b64)} chars base64")
                key = upload_photo(b64, f"{uuid.uuid4().hex}.jpg")
                if not key:
                    logger.error(f"ANALYZE _process_image[{idx}]: S3 upload FAILED")
                    return {"ingredients_text": "", "product_name_hint": "", "all_text": "", "found": False}
                logger.info(f"ANALYZE _process_image[{idx}]: S3 key={key}, running Textract")
                result = extract_all_from_s3(key)
                logger.info(f"ANALYZE _process_image[{idx}]: Textract done, "
                             f"found={result.get('found')}, "
                             f"ingredients_len={len(result.get('ingredients_text', ''))}")
                return result

            textract_results: list[dict] = []
            with ThreadPoolExecutor(max_workers=min(len(all_images), 5)) as ex:
                futs = [ex.submit(_process_image, img, i) for i, img in enumerate(all_images)]
                for fut in futs:
                    try:
                        textract_results.append(fut.result())
                    except Exception as e:
                        logger.error(f"ANALYZE image Textract exception: {e}", exc_info=True)

            logger.info(f"ANALYZE: {len(textract_results)} Textract results collected")
            merged = merge_textract_results(textract_results) if textract_results else {}
            ingredients_text = merged.get("ingredients_text", "")
            ingredients_found = merged.get("found", False)

            if ingredients_text:
                ingredient_source = "textract"
                logger.info(f"ANALYZE: Textract SUCCESS, ingredients_len={len(ingredients_text)}")
            else:
                logger.warning("ANALYZE: Textract found NO ingredients in any photo — falling back to OBF")
                obf = fetch_ingredients(display_name)
                ingredients_text = obf.get("ingredients_text") or ""
                ingredients_found = obf.get("found", False)
                if ingredients_text:
                    ingredient_source = "obf"
                logger.info(f"ANALYZE OBF fallback: found={ingredients_found}")
        else:
            logger.info("ANALYZE: no images, using Open Beauty Facts")
            obf = fetch_ingredients(display_name)
            ingredients_text = obf.get("ingredients_text") or ""
            ingredients_found = obf.get("found", False)
            if ingredients_text:
                ingredient_source = "obf"
            logger.info(f"ANALYZE OBF: found={ingredients_found}")

        # ── 4b. Web research fallback (Nova 2 Lite) ──────────────────────────
        if not ingredients_text:
            logger.info("ANALYZE: no ingredients from Textract or OBF — trying web research")
            research = research_product_ingredients(display_name)
            ingredients_text = research.get("ingredients_text") or ""
            ingredients_found = research.get("found", False)
            if ingredients_text:
                ingredient_source = "web_research"
                logger.info(f"ANALYZE web research SUCCESS, ingredients_len={len(ingredients_text)}")
            else:
                ingredient_source = "not_found"
                logger.info("ANALYZE web research: no ingredients found")

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
            "ingredient_source": ingredient_source,
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

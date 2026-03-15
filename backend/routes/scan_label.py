"""
POST /api/scan-label

Accepts a base64-encoded product label photo, uploads it to S3, then
runs Textract (ingredient extraction) and Rekognition (label/skin-type
detection) in sequence.  Returns a lightweight summary for the frontend
to pre-fill the product name and skin type fields.
"""

import logging
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.s3_service import upload_photo
from services.textract_service import extract_all_from_s3
from services.rekognition_service import detect_product_from_s3

logger = logging.getLogger(__name__)
router = APIRouter()


class ScanLabelRequest(BaseModel):
    image_base64: str


@router.post("/api/scan-label")
async def scan_label(req: ScanLabelRequest):
    """
    Upload photo → Textract + Rekognition → return product_name, skin_type_hint,
    detected_labels, ingredients_found, s3_key.
    """
    try:
        # ── 1. Upload to S3 ──────────────────────────────────────────────────
        s3_key = upload_photo(req.image_base64, f"{uuid.uuid4().hex}.jpg")
        if not s3_key:
            raise HTTPException(status_code=502, detail="S3 upload failed")

        logger.info(f"scan-label: uploaded to s3_key={s3_key}")

        # ── 2. Textract: extract ingredients + product name hint ─────────────
        textract = extract_all_from_s3(s3_key)
        product_name = textract.get("product_name_hint", "")
        ingredients_found = textract.get("found", False)

        # ── 3. Rekognition: detect product type + skin type hint ─────────────
        rek = detect_product_from_s3(s3_key)
        detected_labels = rek.get("detected_labels", [])
        skin_type_hint = rek.get("skin_type_hint")

        # ── 4. Merge: fall back to top Rekognition label if Textract has no name ──
        if not product_name and detected_labels:
            product_name = detected_labels[0]
            logger.info(f"scan-label: product_name fallback from Rekognition: '{product_name}'")

        logger.info(
            f"scan-label: product_name='{product_name}' skin_type_hint={skin_type_hint} "
            f"labels={detected_labels} ingredients_found={ingredients_found}"
        )

        return {
            "product_name": product_name,
            "skin_type_hint": skin_type_hint,
            "detected_labels": detected_labels,
            "ingredients_found": ingredients_found,
            "s3_key": s3_key,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"scan-label error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Label scan failed. Please try again.")

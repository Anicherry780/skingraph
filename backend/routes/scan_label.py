"""
POST /api/scan-label

Accepts one or more base64 images of product label photos.
Uploads each to S3 → Textract + Rekognition in parallel.
Merges results and returns detected product info for frontend auto-fill.
"""

import logging
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from services.s3_service import upload_photo
from services.textract_service import extract_all_from_s3, merge_textract_results
from services.rekognition_service import detect_product_from_s3

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_IMAGES = 5


class ScanLabelRequest(BaseModel):
    images_base64: list[str] = []
    # Backward compat: single image
    image_base64: Optional[str] = None

    @field_validator("images_base64")
    @classmethod
    def check_max(cls, v: list[str]) -> list[str]:
        if len(v) > MAX_IMAGES:
            raise ValueError(f"Maximum {MAX_IMAGES} photos allowed")
        return v

    def get_all_images(self) -> list[str]:
        """Return unified list of base64 strings."""
        images = list(self.images_base64)
        if self.image_base64 and self.image_base64 not in images:
            images.append(self.image_base64)
        return images[:MAX_IMAGES]


def _process_one_image(base64: str, idx: int, total: int) -> dict:
    """Upload one image to S3, run Textract + Rekognition, return merged info."""
    logger.info(f"scan-label: processing image {idx + 1}/{total}")
    s3_key = upload_photo(base64, f"{uuid.uuid4().hex}.jpg")
    if not s3_key:
        logger.warning(f"scan-label: S3 upload failed for image {idx + 1}")
        return {
            "textract": {"ingredients_text": "", "product_name_hint": "", "all_text": "", "found": False},
            "rekognition": {"product_type": "Skincare Product", "detected_labels": [], "skin_type_hint": None, "top_confidence": 0.0},
            "s3_key": "",
        }
    textract = extract_all_from_s3(s3_key)
    rek = detect_product_from_s3(s3_key)
    return {"textract": textract, "rekognition": rek, "s3_key": s3_key}


@router.post("/api/scan-label")
async def scan_label(req: ScanLabelRequest):
    images = req.get_all_images()
    if not images:
        raise HTTPException(status_code=422, detail="No images provided")

    total = len(images)
    logger.info(f"scan-label: {total} image(s) received")

    try:
        # Process all images in parallel
        results = [None] * total
        with ThreadPoolExecutor(max_workers=min(total, MAX_IMAGES)) as ex:
            futs = {
                ex.submit(_process_one_image, img, i, total): i
                for i, img in enumerate(images)
            }
            for fut in as_completed(futs):
                idx = futs[fut]
                try:
                    results[idx] = fut.result()
                except Exception as e:
                    logger.warning(f"scan-label image {idx + 1} failed: {e}")
                    results[idx] = {
                        "textract": {"ingredients_text": "", "product_name_hint": "", "all_text": "", "found": False},
                        "rekognition": {"detected_labels": [], "skin_type_hint": None},
                        "s3_key": "",
                    }

        # Merge Textract results
        textract_results = [r["textract"] for r in results if r]
        merged = merge_textract_results(textract_results)

        # Pick best Rekognition result (skin type hint from any photo)
        skin_type_hint = None
        all_labels: list[str] = []
        for r in results:
            if r and r["rekognition"]:
                rek = r["rekognition"]
                if not skin_type_hint and rek.get("skin_type_hint"):
                    skin_type_hint = rek["skin_type_hint"]
                all_labels.extend(rek.get("detected_labels", []))

        # Deduplicate labels
        seen_labels: set[str] = set()
        unique_labels = [l for l in all_labels if not (l in seen_labels or seen_labels.add(l))]

        product_name = merged.get("product_name_hint", "")
        # Fallback: use top Rekognition label if Textract found no product name
        if not product_name and unique_labels:
            product_name = unique_labels[0]

        s3_keys = [r["s3_key"] for r in results if r and r.get("s3_key")]

        logger.info(
            f"scan-label merged: product_name={repr(product_name)}, "
            f"skin_type_hint={skin_type_hint}, ingredients_found={merged['found']}, "
            f"labels={unique_labels[:5]}"
        )

        return {
            "product_name": product_name,
            "skin_type_hint": skin_type_hint,
            "detected_labels": unique_labels[:5],
            "ingredients_found": merged["found"],
            "s3_keys": s3_keys,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"scan-label error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Label scan failed.")

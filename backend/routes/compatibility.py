"""
POST /api/compatibility

Rule-based routine compatibility checker.
Detects known ingredient conflicts across two products.
Keyword extraction covers product names (e.g. "Retinol Serum" → retinol)
so Product 2 doesn't need a full prior analysis.
"""

import logging
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Known conflict pairs ──────────────────────────────────────────────────────

KNOWN_CONFLICTS = [
    {
        "pair": ["retinol", "vitamin c"],
        "reason": "Can cause irritation when layered. Vitamin C works best in AM, retinol in PM.",
        "severity": "warning",
    },
    {
        "pair": ["retinol", "ascorbic acid"],
        "reason": "Ascorbic acid (Vitamin C) and retinol together can cause sensitivity. Use at different times.",
        "severity": "warning",
    },
    {
        "pair": ["aha", "retinol"],
        "reason": "Both exfoliate — combining risks over-exfoliation and barrier damage.",
        "severity": "warning",
    },
    {
        "pair": ["glycolic acid", "retinol"],
        "reason": "Two exfoliants — use on alternating nights to avoid irritation.",
        "severity": "warning",
    },
    {
        "pair": ["lactic acid", "retinol"],
        "reason": "AHA + retinol increases photosensitivity and irritation risk.",
        "severity": "caution",
    },
    {
        "pair": ["benzoyl peroxide", "retinol"],
        "reason": "Benzoyl peroxide oxidizes retinol, making it ineffective. Use at different times of day.",
        "severity": "avoid",
    },
    {
        "pair": ["salicylic acid", "retinol"],
        "reason": "Both are strong actives — layering can cause dryness and irritation.",
        "severity": "caution",
    },
    {
        "pair": ["niacinamide", "vitamin c"],
        "reason": "At high concentrations may reduce Vitamin C effectiveness. Generally fine at standard levels.",
        "severity": "caution",
    },
    {
        "pair": ["aha", "bha"],
        "reason": "Multiple exfoliants together increase skin sensitivity risk.",
        "severity": "caution",
    },
    {
        "pair": ["glycolic acid", "salicylic acid"],
        "reason": "Two chemical exfoliants — alternate use to avoid over-exfoliation.",
        "severity": "caution",
    },
    {
        "pair": ["retinoid", "vitamin c"],
        "reason": "Retinoids and Vitamin C together can cause irritation. Use AM/PM split.",
        "severity": "warning",
    },
    {
        "pair": ["copper peptides", "vitamin c"],
        "reason": "Copper can oxidize Vitamin C, reducing its effectiveness.",
        "severity": "caution",
    },
    {
        "pair": ["copper peptides", "retinol"],
        "reason": "May counteract each other's benefits — use on alternating nights.",
        "severity": "caution",
    },
]

# Keyword aliases — maps product name keywords to ingredient names used in conflict pairs
INGREDIENT_KEYWORDS: dict = {
    "retinol": "retinol",
    "retinoid": "retinoid",
    "retin-a": "retinol",
    "tretinoin": "retinol",
    "vitamin c": "vitamin c",
    "vit c": "vitamin c",
    "ascorbic": "ascorbic acid",
    "ascorbic acid": "ascorbic acid",
    "niacinamide": "niacinamide",
    "salicylic": "salicylic acid",
    "salicylic acid": "salicylic acid",
    "bha": "bha",
    "glycolic": "glycolic acid",
    "glycolic acid": "glycolic acid",
    "lactic acid": "lactic acid",
    "aha": "aha",
    "benzoyl peroxide": "benzoyl peroxide",
    "benzoyl": "benzoyl peroxide",
    "copper peptide": "copper peptides",
    "copper": "copper peptides",
    "exfoliant": "aha",
    "exfoliating": "aha",
    "peeling": "aha",
}


def _extract_keywords(text: str) -> List[str]:
    """Extract known ingredient keywords from a product name or ingredient list."""
    lower = text.lower()
    found = set()
    # Sort by length so longer phrases match first
    for kw in sorted(INGREDIENT_KEYWORDS.keys(), key=len, reverse=True):
        if kw in lower:
            found.add(INGREDIENT_KEYWORDS[kw])
    return list(found)


# ── Request model ─────────────────────────────────────────────────────────────

class CompatibilityRequest(BaseModel):
    product1_name: str
    product1_ingredients: List[str] = []
    product2_name: str
    product2_ingredients: List[str] = []
    skin_type: str = "combination"


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/api/compatibility")
async def check_compatibility(req: CompatibilityRequest):
    logger.info(f"Compatibility: '{req.product1_name}' + '{req.product2_name}'")
    try:
        # Build ingredient sets for each product
        # Combine passed ingredient names + keywords extracted from the product name
        p1_text = " ".join(req.product1_ingredients) + " " + req.product1_name
        p2_text = " ".join(req.product2_ingredients) + " " + req.product2_name

        p1_keywords = set(_extract_keywords(p1_text))
        p2_keywords = set(_extract_keywords(p2_text))
        all_keywords = p1_keywords | p2_keywords

        logger.info(f"P1 keywords: {p1_keywords} | P2 keywords: {p2_keywords}")

        conflicts = []
        for conflict in KNOWN_CONFLICTS:
            pair = conflict["pair"]
            # Check whether both ingredients in the pair are present across the two products
            # (at least one in each product, or both across them)
            pair_in_p1 = [c for c in pair if c in p1_keywords]
            pair_in_p2 = [c for c in pair if c in p2_keywords]

            # Conflict fires if the pair is split across both products
            if pair_in_p1 and pair_in_p2 and pair_in_p1 != pair_in_p2:
                conflicts.append({
                    "ingredients": pair,
                    "reason": conflict["reason"],
                    "severity": conflict["severity"],
                })
            # Also fire if both are present in the combined set
            elif all(c in all_keywords for c in pair) and not conflicts:
                conflicts.append({
                    "ingredients": pair,
                    "reason": conflict["reason"],
                    "severity": conflict["severity"],
                })

        # Deduplicate
        seen = set()
        unique_conflicts = []
        for c in conflicts:
            key = tuple(sorted(c["ingredients"]))
            if key not in seen:
                seen.add(key)
                unique_conflicts.append(c)

        compatible = len(unique_conflicts) == 0
        worst_severity = None
        if unique_conflicts:
            order = {"avoid": 0, "warning": 1, "caution": 2}
            unique_conflicts.sort(key=lambda x: order.get(x["severity"], 3))
            worst_severity = unique_conflicts[0]["severity"]

        return {
            "product1": req.product1_name,
            "product2": req.product2_name,
            "compatible": compatible,
            "verdict": "Safe to use together" if compatible else "Conflict detected",
            "worst_severity": worst_severity,
            "conflicts": unique_conflicts,
            "recommendation": (
                "These products work well in the same routine."
                if compatible
                else "Use these products at different times of day or on alternating days."
            ),
        }

    except Exception as e:
        logger.error(f"Compatibility error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Compatibility check failed.")

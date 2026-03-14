from typing import Tuple

SKIN_TYPE_MAP = {
    # DRY — high confidence
    "moisturizer":      ("dry", "high", "Moisturizers target dry skin"),
    "moisturising":     ("dry", "high", "Moisturising products target dry skin"),
    "moisturizing":     ("dry", "high", "Moisturizing products target dry skin"),
    "hyaluronic acid":  ("dry", "high", "Hyaluronic acid hydrates dry skin"),
    "hydrating":        ("dry", "high", "Hydrating products target dry skin"),
    "butter":           ("dry", "high", "Body butters are for very dry skin"),
    "balm":             ("dry", "high", "Balms target dry or sensitive skin"),
    "rich":             ("dry", "medium", "Rich formulas suit dry skin"),
    "cream":            ("dry", "medium", "Cream textures suit dry skin"),
    "lotion":           ("dry", "medium", "Lotions are typically for dry skin"),
    "oil":              ("dry", "medium", "Face oils are used for dry skin"),

    # OILY — high confidence
    "niacinamide":      ("oily", "high", "Niacinamide controls sebum and minimizes pores"),
    "salicylic acid":   ("oily", "high", "Salicylic acid is an oil-soluble exfoliant for oily skin"),
    "bha":              ("oily", "high", "BHA targets oily and acne-prone skin"),
    "matte":            ("oily", "high", "Matte products control shine on oily skin"),
    "mattifying":       ("oily", "high", "Mattifying products control oil"),
    "oil control":      ("oily", "high", "Oil control products target oily skin"),
    "clay":             ("oily", "high", "Clay absorbs excess oil"),
    "charcoal":         ("oily", "high", "Charcoal targets pores and oil"),
    "pore":             ("oily", "high", "Pore products are for oily skin"),
    "acne":             ("oily", "high", "Acne products target oily/acne-prone skin"),
    "benzoyl peroxide": ("oily", "high", "Benzoyl peroxide treats oily acne-prone skin"),
    "zinc":             ("oily", "medium", "Zinc regulates oil production"),

    # SENSITIVE — high confidence
    "soothing":         ("sensitive", "high", "Soothing products are for sensitive skin"),
    "centella":         ("sensitive", "high", "Centella asiatica is a sensitive skin ingredient"),
    "cica":             ("sensitive", "high", "Cica treats sensitive and irritated skin"),
    "barrier":          ("sensitive", "high", "Barrier repair products target sensitive skin"),
    "calming":          ("sensitive", "high", "Calming products are for sensitive skin"),
    "redness":          ("sensitive", "high", "Redness-targeting products are for sensitive skin"),
    "for sensitive":    ("sensitive", "high", "Explicitly labeled for sensitive skin"),
    "gentle":           ("sensitive", "medium", "Gentle products suit sensitive skin"),
    "aloe":             ("sensitive", "medium", "Aloe vera soothes sensitive skin"),

    # COMBINATION — medium/low confidence (universal products)
    "water gel":        ("combination", "high", "Water gel textures suit combination skin"),
    "glycolic acid":    ("combination", "medium", "AHA exfoliants suit combination skin"),
    "aha":              ("combination", "medium", "AHA exfoliants suit combination skin"),
    "lactic acid":      ("combination", "medium", "Lactic acid suits combination skin"),
    "gel":              ("combination", "medium", "Gel textures work well for combination skin"),
    "serum":            ("combination", "low", "Serums are used across skin types"),
    "essence":          ("combination", "low", "Essences suit combination skin as middle ground"),
    "toner":            ("combination", "low", "Toners work across skin types"),
    "sunscreen":        ("combination", "low", "Sunscreen is universal"),
    "spf":              ("combination", "low", "SPF products are universal"),
    "retinol":          ("combination", "low", "Retinol is used across skin types"),
    "retinoid":         ("combination", "low", "Retinoids work for multiple skin types"),
    "vitamin c":        ("combination", "low", "Vitamin C is used across skin types"),
}


def infer_skin_type(product_name: str) -> Tuple[str, bool, str]:
    """
    Returns: (skin_type, was_inferred, reason)
    skin_type: "dry" | "oily" | "sensitive" | "combination"
    was_inferred: True if matched a keyword, False if used default
    reason: human-readable explanation shown to user
    """
    text = product_name.lower()

    # Sort by keyword length — longer phrases take priority over shorter ones
    sorted_keywords = sorted(SKIN_TYPE_MAP.keys(), key=len, reverse=True)

    for keyword in sorted_keywords:
        if keyword in text:
            skin_type, _confidence, reason = SKIN_TYPE_MAP[keyword]
            return skin_type, True, reason

    # No keyword matched — return combination as safe default
    return "combination", False, "No specific skin type signals found — defaulting to combination"

export type SkinType = "oily" | "dry" | "combination" | "sensitive" | null;

export interface InferenceResult {
  skinType: SkinType;
  confidence: "high" | "medium" | "low";
  reason: string;
  matchedKeyword: string;
}

const SKIN_TYPE_MAP: Record<string, { type: SkinType; confidence: "high" | "medium" | "low"; reason: string }> = {
  // DRY skin keywords
  "moisturizer":      { type: "dry",         confidence: "high",   reason: "Moisturizers are primarily for dry skin" },
  "moisturising":     { type: "dry",         confidence: "high",   reason: "Moisturising products target dry skin" },
  "moisturizing":     { type: "dry",         confidence: "high",   reason: "Moisturizing products target dry skin" },
  "cream":            { type: "dry",         confidence: "medium", reason: "Cream textures suit dry skin best" },
  "lotion":           { type: "dry",         confidence: "medium", reason: "Lotions are typically for dry skin" },
  "butter":           { type: "dry",         confidence: "high",   reason: "Body butters are for very dry skin" },
  "hyaluronic acid":  { type: "dry",         confidence: "high",   reason: "Hyaluronic acid is a hydration ingredient for dry skin" },
  "hydrating":        { type: "dry",         confidence: "high",   reason: "Hydrating products target dry skin" },
  "rich":             { type: "dry",         confidence: "medium", reason: "Rich formulas suit dry skin" },
  "balm":             { type: "dry",         confidence: "high",   reason: "Balms target very dry or sensitive skin" },
  "oil":              { type: "dry",         confidence: "medium", reason: "Face oils are used for dry skin" },

  // OILY skin keywords
  "matte":            { type: "oily",        confidence: "high",   reason: "Matte products are specifically for oily skin" },
  "mattifying":       { type: "oily",        confidence: "high",   reason: "Mattifying products control oil" },
  "oil control":      { type: "oily",        confidence: "high",   reason: "Oil control products target oily skin" },
  "clay":             { type: "oily",        confidence: "high",   reason: "Clay ingredients absorb excess oil" },
  "charcoal":         { type: "oily",        confidence: "high",   reason: "Charcoal targets pores and oil" },
  "pore":             { type: "oily",        confidence: "high",   reason: "Pore products are for oily skin" },
  "niacinamide":      { type: "oily",        confidence: "high",   reason: "Niacinamide controls sebum and minimizes pores" },
  "salicylic acid":   { type: "oily",        confidence: "high",   reason: "Salicylic acid is an oil-soluble exfoliant for oily/acne skin" },
  "bha":              { type: "oily",        confidence: "high",   reason: "BHA (salicylic) is for oily and acne-prone skin" },
  "acne":             { type: "oily",        confidence: "high",   reason: "Acne products target oily/acne-prone skin" },
  "benzoyl peroxide": { type: "oily",        confidence: "high",   reason: "Benzoyl peroxide treats acne on oily skin" },
  "zinc":             { type: "oily",        confidence: "medium", reason: "Zinc regulates oil production" },

  // SENSITIVE skin keywords
  "soothing":         { type: "sensitive",   confidence: "high",   reason: "Soothing products are for sensitive skin" },
  "centella":         { type: "sensitive",   confidence: "high",   reason: "Centella asiatica is a sensitive skin ingredient" },
  "cica":             { type: "sensitive",   confidence: "high",   reason: "Cica is used for sensitive and irritated skin" },
  "barrier":          { type: "sensitive",   confidence: "high",   reason: "Barrier repair products target sensitive skin" },
  "calming":          { type: "sensitive",   confidence: "high",   reason: "Calming products are for sensitive skin" },
  "redness":          { type: "sensitive",   confidence: "high",   reason: "Redness-targeting products are for sensitive skin" },
  "for sensitive":    { type: "sensitive",   confidence: "high",   reason: "Explicitly labeled for sensitive skin" },
  "fragrance":        { type: "sensitive",   confidence: "medium", reason: "Fragrance-free products often target sensitive skin" },
  "gentle":           { type: "sensitive",   confidence: "medium", reason: "Gentle products suit sensitive skin" },
  "aloe":             { type: "sensitive",   confidence: "medium", reason: "Aloe vera soothes sensitive skin" },

  // COMBINATION skin keywords (default for general/universal products)
  "water gel":        { type: "combination", confidence: "high",   reason: "Water gel textures suit combination skin" },
  "glycolic acid":    { type: "combination", confidence: "medium", reason: "AHA exfoliants suit combination skin" },
  "aha":              { type: "combination", confidence: "medium", reason: "AHA exfoliants suit combination skin" },
  "lactic acid":      { type: "combination", confidence: "medium", reason: "Lactic acid is gentler, suits combination skin" },
  "gel":              { type: "combination", confidence: "medium", reason: "Gel textures work well for combination skin" },
  "serum":            { type: "combination", confidence: "low",    reason: "Serums are used across all skin types; defaulting to combination" },
  "essence":          { type: "combination", confidence: "low",    reason: "Essences suit combination skin as a middle ground" },
  "toner":            { type: "combination", confidence: "low",    reason: "Toners work across skin types; defaulting to combination" },
  "sunscreen":        { type: "combination", confidence: "low",    reason: "Sunscreen is universal; defaulting to combination" },
  "spf":              { type: "combination", confidence: "low",    reason: "SPF products are universal; defaulting to combination" },
  "retinol":          { type: "combination", confidence: "low",    reason: "Retinol is used across skin types; defaulting to combination" },
  "retinoid":         { type: "combination", confidence: "low",    reason: "Retinoids work for multiple skin types" },
  "vitamin c":        { type: "combination", confidence: "low",    reason: "Vitamin C is used across skin types" },
};

export function inferSkinType(productName: string): InferenceResult {
  const lower = productName.toLowerCase();

  // Sort by keyword length — longer multi-word matches take priority
  const sortedKeys = Object.keys(SKIN_TYPE_MAP).sort((a, b) => b.length - a.length);

  for (const keyword of sortedKeys) {
    if (lower.includes(keyword)) {
      return {
        skinType: SKIN_TYPE_MAP[keyword].type,
        confidence: SKIN_TYPE_MAP[keyword].confidence,
        reason: SKIN_TYPE_MAP[keyword].reason,
        matchedKeyword: keyword,
      };
    }
  }

  return {
    skinType: null,
    confidence: "low",
    reason: "",
    matchedKeyword: "",
  };
}

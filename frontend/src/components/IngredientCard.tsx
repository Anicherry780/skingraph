import React from "react";
import "./IngredientCard.css";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface IngredientCardProps {
  name: string;
  category: string;
  is_flagged: boolean;
  flag_reason: string | null;
  description: string;
  irritant_risk: "none" | "low" | "medium" | "high";
  comedogenic_rating: number; // 0–5
  safe_for_skin_type: "safe" | "caution" | "avoid";
}

// ── Constants ─────────────────────────────────────────────────────────────────

const CATEGORY_COLORS: Record<string, string> = {
  moisturizer: "#1D9E75",
  humectant:   "#1D9E75",
  antioxidant: "#1D9E75",
  emollient:   "#085041",
  occlusive:   "#085041",
  active:      "#BA7517",
  exfoliant:   "#BA7517",
  fragrance:   "#E24B4A",
  preservative:"#6B7280",
  surfactant:  "#6B7280",
  other:       "#9CA3AF",
};

const IRRITANT_COLORS: Record<string, string> = {
  none:   "#1D9E75",
  low:    "#BA7517",
  medium: "#E07B00",
  high:   "#E24B4A",
};

const SAFE_STYLES: Record<string, { bg: string; color: string }> = {
  safe:    { bg: "#E1F5EE", color: "#085041" },
  caution: { bg: "#FEF3C7", color: "#92400E" },
  avoid:   { bg: "#FEE2E2", color: "#991B1B" },
};

// ── Sub-components ────────────────────────────────────────────────────────────

function ComedogenicDots({ rating }: { rating: number }) {
  const clamped = Math.min(5, Math.max(0, rating));
  return (
    <div className="comed-dots" title={`Comedogenic rating: ${clamped}/5`}>
      {Array.from({ length: 5 }).map((_, i) => (
        <span key={i} className={`comed-dot${i < clamped ? " filled" : ""}`} />
      ))}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

const IngredientCard: React.FC<IngredientCardProps> = ({
  name,
  category,
  is_flagged,
  flag_reason,
  description,
  irritant_risk,
  comedogenic_rating,
  safe_for_skin_type,
}) => {
  const safeStyle = SAFE_STYLES[safe_for_skin_type] ?? SAFE_STYLES.safe;

  return (
    <div className={`ingredient-card${is_flagged ? " flagged" : ""}`}>
      {/* Name + category */}
      <div className="ingredient-top">
        <span className="ingredient-name">{name}</span>
        <span
          className="cat-badge"
          style={{ background: CATEGORY_COLORS[category] ?? "#9CA3AF" }}
        >
          {category}
        </span>
      </div>

      {/* Description */}
      <p className="ingredient-desc">{description}</p>

      {/* Meta row: irritant risk · comedogenic dots · safe chip */}
      <div className="ingredient-meta">
        <span
          className="irritant-pill"
          style={{ color: IRRITANT_COLORS[irritant_risk] ?? "#9CA3AF" }}
        >
          Irritant: {irritant_risk}
        </span>

        <div className="comed-wrapper">
          <span className="comed-label">Comed.</span>
          <ComedogenicDots rating={comedogenic_rating} />
        </div>

        <span className="safe-chip" style={safeStyle}>
          {safe_for_skin_type}
        </span>
      </div>

      {/* Flag note */}
      {is_flagged && flag_reason && (
        <p className="ingredient-flag-note">⚠️ {flag_reason}</p>
      )}
    </div>
  );
};

export default IngredientCard;

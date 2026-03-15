import React from "react";
import "./AlternativesGrid.css";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface Alternative {
  name: string;
  brand: string;
  estimated_price: string;
  match_percent: number;
  key_matching_ingredients: string[];
  why_similar: string;
  amazon_url: string;
}

export interface AlternativesGridProps {
  alternatives: Alternative[];
  loading: boolean;
}

// ── Component ─────────────────────────────────────────────────────────────────

const AlternativesGrid: React.FC<AlternativesGridProps> = ({ alternatives, loading }) => {
  if (loading) {
    return (
      <div className="alt-loading">
        <div className="alt-spinner" />
        <span>Finding cheaper alternatives…</span>
      </div>
    );
  }

  if (!alternatives.length) {
    return (
      <p className="alt-empty">No alternatives found for this product.</p>
    );
  }

  return (
    <div className="alt-grid">
      {alternatives.map((alt, i) => (
        <div key={i} className="alt-card">
          {/* Match badge */}
          <div className="alt-match-badge">{alt.match_percent}% match</div>

          {/* Product info */}
          <p className="alt-brand">{alt.brand}</p>
          <p className="alt-name">{alt.name}</p>

          {/* Price */}
          <p className="alt-price">{alt.estimated_price}</p>

          {/* Matching ingredients */}
          {alt.key_matching_ingredients?.length > 0 && (
            <div className="alt-ingredients">
              {alt.key_matching_ingredients.slice(0, 3).map((ing, j) => (
                <span key={j} className="alt-ing-pill">{ing}</span>
              ))}
            </div>
          )}

          {/* Why similar */}
          <p className="alt-why">{alt.why_similar}</p>

          {/* Amazon link */}
          <a
            className="alt-amazon-btn"
            href={alt.amazon_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            View on Amazon ↗
          </a>
        </div>
      ))}
    </div>
  );
};

export default AlternativesGrid;

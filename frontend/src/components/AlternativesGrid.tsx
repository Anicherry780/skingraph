import React from "react";
import "./AlternativesGrid.css";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface Alternative {
  name: string;
  brand: string;
  match_percent: number;
  shared_count: number;
  has_ingredients: boolean;
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
        <span>Finding similar alternatives…</span>
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
          {/* Match badge — real calculated % or "Similar formula" fallback */}
          {alt.has_ingredients && alt.match_percent > 0 ? (
            <div className="alt-match-badge">
              {alt.match_percent}% match
            </div>
          ) : (
            <div className="alt-match-badge alt-similar-badge">Similar formula</div>
          )}

          {/* Product info */}
          <p className="alt-brand">{alt.brand}</p>
          <p className="alt-name">{alt.name}</p>

          {/* Shared ingredients count */}
          {alt.has_ingredients && alt.shared_count > 0 && (
            <p className="alt-shared">{alt.shared_count} shared ingredient{alt.shared_count !== 1 ? "s" : ""}</p>
          )}

          {/* Matching ingredients */}
          {alt.key_matching_ingredients?.length > 0 && (
            <div className="alt-ingredients">
              {alt.key_matching_ingredients.slice(0, 4).map((ing, j) => (
                <span key={j} className="alt-ing-pill">{ing}</span>
              ))}
            </div>
          )}

          {/* Why similar */}
          <p className="alt-why">{alt.why_similar}</p>

          {/* Amazon link — check real price */}
          <a
            className="alt-amazon-btn"
            href={alt.amazon_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            Check price on Amazon ↗
          </a>
        </div>
      ))}
    </div>
  );
};

export default AlternativesGrid;

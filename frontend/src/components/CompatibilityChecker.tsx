import React from "react";
import "./CompatibilityChecker.css";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface Conflict {
  ingredients: string[];
  reason: string;
  severity: "caution" | "warning" | "avoid";
}

export interface CompatibilityResult {
  product1: string;
  product2: string;
  compatible: boolean;
  verdict: string;
  worst_severity: string | null;
  conflicts: Conflict[];
  recommendation: string;
}

export interface CompatibilityCheckerProps {
  result: CompatibilityResult | null;
  loading: boolean;
  product1: string;
  product2: string;
}

// ── Severity helpers ──────────────────────────────────────────────────────────

const SEV_LABELS: Record<string, string> = {
  caution: "Caution",
  warning: "Warning",
  avoid: "Avoid",
};

const SEV_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  caution: { bg: "#FFFBEB", text: "#92400E", border: "#FCD34D" },
  warning: { bg: "#FFF3CD", text: "#B45309", border: "#F59E0B" },
  avoid:   { bg: "#FEE2E2", text: "#991B1B", border: "#FCA5A5" },
};

// ── Component ─────────────────────────────────────────────────────────────────

const CompatibilityChecker: React.FC<CompatibilityCheckerProps> = ({
  result,
  loading,
  product1,
  product2,
}) => {
  if (loading) {
    return (
      <div className="compat-loading">
        <div className="compat-spinner" />
        <span>Checking routine compatibility…</span>
      </div>
    );
  }

  if (!result) return null;

  return (
    <div className="compat-wrapper">
      {/* Products row */}
      <div className="compat-products">
        <span className="compat-product-chip">{product1}</span>
        <span className="compat-plus">+</span>
        <span className="compat-product-chip">{product2}</span>
      </div>

      {/* Verdict */}
      <div className={`compat-verdict ${result.compatible ? "safe" : "conflict"}`}>
        <span className="compat-verdict-icon">
          {result.compatible ? "✅" : "⚠️"}
        </span>
        <div>
          <p className="compat-verdict-text">{result.verdict}</p>
          <p className="compat-recommendation">{result.recommendation}</p>
        </div>
      </div>

      {/* Conflict details */}
      {result.conflicts.length > 0 && (
        <div className="compat-conflicts">
          {result.conflicts.map((conflict, i) => {
            const style = SEV_COLORS[conflict.severity] ?? SEV_COLORS.caution;
            return (
              <div
                key={i}
                className="compat-conflict-card"
                style={{ background: style.bg, borderColor: style.border }}
              >
                <div className="conflict-top">
                  <span className="conflict-pair">
                    {conflict.ingredients.join(" + ")}
                  </span>
                  <span
                    className="conflict-sev-badge"
                    style={{ background: style.border, color: style.text }}
                  >
                    {SEV_LABELS[conflict.severity] ?? conflict.severity}
                  </span>
                </div>
                <p className="conflict-reason" style={{ color: style.text }}>
                  {conflict.reason}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default CompatibilityChecker;

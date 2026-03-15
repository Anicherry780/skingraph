import React, { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import "./Results.css";

// ── Types ────────────────────────────────────────────────────────────────────

interface Ingredient {
  name: string;
  category: string;
  is_flagged: boolean;
  flag_reason: string | null;
  description: string;
}

interface RedFlag {
  ingredient: string;
  reason: string;
  severity: "low" | "medium" | "high";
}

interface AnalysisResult {
  product_name: string;
  skin_type: string;
  skin_type_inferred: boolean;
  suitability_score: number;
  summary: string;
  ingredients: Ingredient[];
  red_flags: RedFlag[];
  reality_check: string;
  brand_claims: string | null;
  amazon_price: string | null;
  ingredients_found: boolean;
  cached: boolean;
  error?: string;
}

// ── Category badge colours ────────────────────────────────────────────────────

const CATEGORY_COLORS: Record<string, string> = {
  moisturizer: "#1D9E75",
  humectant: "#1D9E75",
  antioxidant: "#1D9E75",
  emollient: "#085041",
  occlusive: "#085041",
  active: "#BA7517",
  exfoliant: "#BA7517",
  fragrance: "#E24B4A",
  preservative: "#6B7280",
  surfactant: "#6B7280",
  other: "#9CA3AF",
};

// ── Helpers ──────────────────────────────────────────────────────────────────

function scoreColor(score: number) {
  if (score >= 75) return "#1D9E75";
  if (score >= 50) return "#BA7517";
  return "#E24B4A";
}

function scoreLabel(score: number, skinType: string) {
  const skin = SKIN_TYPE_LABELS[skinType] ?? skinType;
  if (score >= 80) return `Great for ${skin} skin`;
  if (score >= 65) return `Suitable for ${skin} skin`;
  if (score >= 50) return `Decent for ${skin} skin`;
  if (score >= 35) return "Mixed results";
  return `Not recommended for ${skin} skin`;
}

const SKIN_TYPE_LABELS: Record<string, string> = {
  dry: "Dry",
  oily: "Oily",
  combination: "Combination",
  sensitive: "Sensitive",
};

const LOADING_STEPS = [
  "Looking up ingredients…",
  "Running ingredient analysis…",
  "Checking Amazon price…",
  "Comparing brand claims…",
  "Generating your report…",
];

// ── Circular Score ───────────────────────────────────────────────────────────

function ScoreCircle({ score }: { score: number }) {
  const [animated, setAnimated] = useState(0);
  const color = scoreColor(score);
  const r = 52;
  const circumference = 2 * Math.PI * r;
  const offset = circumference - (animated / 100) * circumference;

  useEffect(() => {
    const t = setTimeout(() => setAnimated(score), 120);
    return () => clearTimeout(t);
  }, [score]);

  return (
    <div className="score-circle-wrapper">
      <svg className="score-svg" viewBox="0 0 120 120" width="140" height="140">
        <circle cx="60" cy="60" r={r} fill="none" stroke="#E5E7EB" strokeWidth="10" />
        <circle
          cx="60" cy="60" r={r}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 60 60)"
          style={{ transition: "stroke-dashoffset 1.2s cubic-bezier(0.4,0,0.2,1)" }}
        />
      </svg>
      <div className="score-inner">
        <span className="score-number" style={{ color }}>{score}</span>
        <span className="score-denom">/100</span>
      </div>
    </div>
  );
}

// ── Main Component ───────────────────────────────────────────────────────────

const Results: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const payload = location.state?.payload;

  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loadingStep, setLoadingStep] = useState(0);
  const hasFetched = useRef(false);

  const API_URL =
    import.meta.env.VITE_API_URL || "https://skingraph-backend.onrender.com";

  // Rotate loading step text
  useEffect(() => {
    if (!loading) return;
    const id = setInterval(() => setLoadingStep((s) => (s + 1) % LOADING_STEPS.length), 2500);
    return () => clearInterval(id);
  }, [loading]);

  // Fetch analysis
  useEffect(() => {
    if (!payload) { navigate("/"); return; }
    if (hasFetched.current) return;
    hasFetched.current = true;

    async function fetchAnalysis() {
      try {
        setLoading(true);
        setError(null);

        const resp = await fetch(`${API_URL}/api/analyze`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (!resp.ok) {
          const detail = await resp.json().catch(() => ({}));
          throw new Error((detail as { detail?: string }).detail || `Server error ${resp.status}`);
        }

        const data: AnalysisResult = await resp.json();
        setResult(data);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Analysis failed. Please try again.");
      } finally {
        setLoading(false);
      }
    }

    fetchAnalysis();
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  if (!payload) return null;

  return (
    <div className="results-page">

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header className="results-header">
        <button className="back-btn" onClick={() => navigate("/")}>← Back</button>
        <span className="logo-text">Skin<span className="logo-green">Graph</span></span>
      </header>

      {/* ── Loading ─────────────────────────────────────────────────────── */}
      {loading && (
        <div className="state-center">
          <div className="spinner" />
          <p className="loading-product">{payload.product_name}</p>
          <p className="loading-step">{LOADING_STEPS[loadingStep]}</p>
        </div>
      )}

      {/* ── Error ───────────────────────────────────────────────────────── */}
      {!loading && error && (
        <div className="state-center">
          <div className="state-icon">⚠️</div>
          <p className="error-title">Analysis failed</p>
          <p className="error-detail">{error}</p>
          <button className="btn-primary" onClick={() => navigate("/")}>
            Try another product
          </button>
        </div>
      )}

      {/* ── Results ─────────────────────────────────────────────────────── */}
      {!loading && result && (
        <main className="results-content">

          {/* Product header */}
          <div className="product-header">
            <div className="product-header-top">
              <h1 className="product-title">{result.product_name}</h1>
              {result.cached && <span className="cached-badge">⚡ Cached</span>}
            </div>
            <div className="product-meta">
              <span className="skin-type-pill">
                {SKIN_TYPE_LABELS[result.skin_type] ?? result.skin_type} skin
                {result.skin_type_inferred && <span className="auto-tag">auto</span>}
              </span>
              {result.amazon_price && (
                <span className="price-pill">🛒 {result.amazon_price} on Amazon</span>
              )}
            </div>
          </div>

          {/* Score card */}
          <section className="score-card">
            <ScoreCircle score={result.suitability_score} />
            <div className="score-info">
              <p
                className="score-label-text"
                style={{ color: scoreColor(result.suitability_score) }}
              >
                {scoreLabel(result.suitability_score, result.skin_type)}
              </p>
              <p className="score-summary">{result.summary}</p>
            </div>
          </section>

          {/* Red flags */}
          {result.red_flags.length > 0 && (
            <section className="r-section">
              <h2 className="section-title">⚠️ Red Flags</h2>
              <div className="red-flags-list">
                {result.red_flags.map((flag, i) => (
                  <div key={i} className={`red-flag-card sev-${flag.severity}`}>
                    <div className="flag-top">
                      <span className="flag-name">{flag.ingredient}</span>
                      <span className={`sev-badge sev-${flag.severity}`}>{flag.severity}</span>
                    </div>
                    <p className="flag-reason">{flag.reason}</p>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Ingredients */}
          {result.ingredients.length > 0 && (
            <section className="r-section">
              <h2 className="section-title">🧪 Ingredient Breakdown</h2>
              {!result.ingredients_found && (
                <p className="note-text">
                  ℹ️ Exact ingredient list not found in Open Beauty Facts — analysis based on common formulation for this product type.
                </p>
              )}
              <div className="ingredients-grid">
                {result.ingredients.map((ing, i) => (
                  <div key={i} className={`ingredient-card${ing.is_flagged ? " flagged" : ""}`}>
                    <div className="ingredient-top">
                      <span className="ingredient-name">{ing.name}</span>
                      <span
                        className="cat-badge"
                        style={{ background: CATEGORY_COLORS[ing.category] ?? "#9CA3AF" }}
                      >
                        {ing.category}
                      </span>
                    </div>
                    <p className="ingredient-desc">{ing.description}</p>
                    {ing.is_flagged && ing.flag_reason && (
                      <p className="ingredient-flag-note">⚠️ {ing.flag_reason}</p>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Brand vs Reality */}
          {result.reality_check && (
            <section className="r-section">
              <h2 className="section-title">🔬 Brand vs Reality</h2>
              {result.brand_claims && (
                <div className="info-box brand-box">
                  <span className="box-label">Brand says</span>
                  <p>{result.brand_claims}</p>
                </div>
              )}
              <div className="info-box reality-box">
                <span className="box-label">Science says</span>
                <p>{result.reality_check}</p>
              </div>
            </section>
          )}

          {/* Analyse another */}
          <div className="analyse-another">
            <button className="btn-primary" onClick={() => navigate("/")}>
              Analyse another product
            </button>
          </div>

        </main>
      )}
    </div>
  );
};

export default Results;

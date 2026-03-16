import React, { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import IngredientCard from "../components/IngredientCard";
import RedFlagAlert from "../components/RedFlagAlert";
import AlternativesGrid, { type Alternative } from "../components/AlternativesGrid";
import CompatibilityChecker, { type CompatibilityResult } from "../components/CompatibilityChecker";
import "./Results.css";

// ── Types ────────────────────────────────────────────────────────────────────

interface Ingredient {
  name: string;
  category: string;
  is_flagged: boolean;
  flag_reason: string | null;
  description: string;
  irritant_risk: "none" | "low" | "medium" | "high";
  comedogenic_rating: number;
  safe_for_skin_type: "safe" | "caution" | "avoid";
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
  corrected_name?: string | null;
  ingredient_source?: "textract" | "obf" | "obf_research" | "web_research" | "estimated" | "not_found";
}

// ── Constants ────────────────────────────────────────────────────────────────

const SKIN_TYPE_LABELS: Record<string, string> = {
  dry: "Dry",
  oily: "Oily",
  combination: "Combination",
  sensitive: "Sensitive",
};

const SKIN_TYPES = ["oily", "dry", "combination", "sensitive"] as const;

const LOADING_STEPS_DEFAULT = [
  "Looking up ingredients…",
  "Running ingredient analysis…",
  "Comparing brand claims…",
  "Generating your report…",
];

const LOADING_STEPS_IMAGE = [
  "Reading label text…",
  "Extracting ingredients from photo…",
  "Running ingredient analysis…",
  "Comparing brand claims…",
  "Generating your report…",
];

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

// ── Collapsible Ingredients Section ──────────────────────────────────────

const INGREDIENTS_COLLAPSED_COUNT = 12;

function IngredientsSection({
  ingredients,
  ingredientsFound,
  ingredientSource,
}: {
  ingredients: Ingredient[];
  ingredientsFound: boolean;
  ingredientSource?: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const hasMore = ingredients.length > INGREDIENTS_COLLAPSED_COUNT;
  const visible = expanded ? ingredients : ingredients.slice(0, INGREDIENTS_COLLAPSED_COUNT);
  const remaining = ingredients.length - INGREDIENTS_COLLAPSED_COUNT;

  return (
    <section className="r-section">
      <h2 className="section-title">🧪 Ingredient Breakdown</h2>
      {!ingredientsFound && ingredientSource !== "estimated" && ingredientSource !== "web_research" && (
        <p className="note-text">
          ℹ️ Exact ingredient list not found — analysis based on common formulation for this product type.
        </p>
      )}
      <div className={`ingredients-grid-wrapper${!expanded && hasMore ? " collapsed" : ""}`}>
        <div className="ingredients-grid">
          {visible.map((ing, i) => (
            <IngredientCard
              key={i}
              name={ing.name}
              category={ing.category}
              is_flagged={ing.is_flagged}
              flag_reason={ing.flag_reason}
              description={ing.description}
              irritant_risk={ing.irritant_risk ?? "none"}
              comedogenic_rating={ing.comedogenic_rating ?? 0}
              safe_for_skin_type={ing.safe_for_skin_type ?? "safe"}
            />
          ))}
        </div>
      </div>
      {hasMore && (
        <button
          className="btn-show-more"
          onClick={() => setExpanded((prev) => !prev)}
        >
          {expanded ? "Show less ↑" : `Show ${remaining} more ingredients ↓`}
        </button>
      )}
    </section>
  );
}

// ── Main Component ───────────────────────────────────────────────────────────

const Results: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const payload = location.state?.payload;

  // ── Main analysis state ────────────────────────────────────────────────
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loadingStep, setLoadingStep] = useState(0);
  const hasFetched = useRef(false);

  // ── Phase 3: Alternatives state ────────────────────────────────────────
  const [alternatives, setAlternatives] = useState<Alternative[]>([]);
  const [altLoading, setAltLoading] = useState(false);

  // ── Phase 3: Compatibility state ───────────────────────────────────────
  const [compatibility, setCompatibility] = useState<CompatibilityResult | null>(null);
  const [compatLoading, setCompatLoading] = useState(false);

  const API_URL =
    import.meta.env.VITE_API_URL || "https://skingraph-backend.onrender.com";

  // ── Shared analysis fetch ──────────────────────────────────────────────

  const runAnalysis = async (requestPayload: object) => {
    setLoading(true);
    setError(null);
    // Reset secondary sections on re-analyze
    setAlternatives([]);
    setCompatibility(null);
    try {
      const resp = await fetch(`${API_URL}/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...(requestPayload as Record<string, unknown>),
          images_base64: (requestPayload as { images_base64?: string[]; image_base64?: string }).images_base64
            ?? ((requestPayload as { image_base64?: string }).image_base64
              ? [(requestPayload as { image_base64: string }).image_base64]
              : []),
        }),
      });
      if (!resp.ok) {
        const detail = await resp.json().catch(() => ({}));
        throw new Error(
          (detail as { detail?: string }).detail || `Server error ${resp.status}`
        );
      }
      const data: AnalysisResult = await resp.json();
      setResult(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Analysis failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  // ── Initial fetch ──────────────────────────────────────────────────────

  useEffect(() => {
    if (!payload) { navigate("/"); return; }
    if (hasFetched.current) return;
    hasFetched.current = true;
    runAnalysis(payload);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Re-analyze with new skin type ──────────────────────────────────────

  const reAnalyze = (newSkinType: string) => {
    runAnalysis({ ...payload, skin_type: newSkinType, skin_type_inferred: false });
  };

  // ── Loading step ticker ────────────────────────────────────────────────

  const loadingSteps = ((payload?.images_base64?.length ?? 0) > 0 || !!payload?.image_base64)
    ? LOADING_STEPS_IMAGE
    : LOADING_STEPS_DEFAULT;

  useEffect(() => {
    if (!loading) return;
    const id = setInterval(() => setLoadingStep((s) => (s + 1) % loadingSteps.length), 2500);
    return () => clearInterval(id);
  }, [loading]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Fetch alternatives once main analysis completes ────────────────────

  useEffect(() => {
    if (!result || loading) return;

    async function fetchAlternatives() {
      setAltLoading(true);
      try {
        const ingredientNames = result!.ingredients.map((i) => i.name);
        const resp = await fetch(`${API_URL}/api/alternatives`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            product_name: result!.product_name,
            skin_type: result!.skin_type,
            key_ingredients: ingredientNames,
          }),
        });
        if (resp.ok) {
          const data = await resp.json();
          setAlternatives(data.alternatives ?? []);
        }
      } catch (e) {
        console.warn("Alternatives fetch failed:", e);
      } finally {
        setAltLoading(false);
      }
    }

    fetchAlternatives();
  }, [result?.product_name, result?.skin_type]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Fetch compatibility if second product was entered ──────────────────

  useEffect(() => {
    if (!result || loading || !payload?.second_product) return;

    async function fetchCompatibility() {
      setCompatLoading(true);
      try {
        const ingredientNames = result!.ingredients.map((i) => i.name);
        const resp = await fetch(`${API_URL}/api/compatibility`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            product1_name: result!.product_name,
            product1_ingredients: ingredientNames,
            product2_name: payload.second_product,
            product2_ingredients: [],
            skin_type: result!.skin_type,
          }),
        });
        if (resp.ok) {
          const data: CompatibilityResult = await resp.json();
          setCompatibility(data);
        }
      } catch (e) {
        console.warn("Compatibility fetch failed:", e);
      } finally {
        setCompatLoading(false);
      }
    }

    fetchCompatibility();
  }, [result?.product_name]); // eslint-disable-line react-hooks/exhaustive-deps

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
          <p className="loading-step">{loadingSteps[loadingStep]}</p>
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

          {/* ── Inference banner ────────────────────────────────────────── */}
          {result.skin_type_inferred && (
            <div className="inference-banner">
              <div className="inference-banner-text">
                <span className="inference-icon">ℹ️</span>
                <div>
                  <p>
                    We analyzed this as{" "}
                    <strong>{SKIN_TYPE_LABELS[result.skin_type] ?? result.skin_type} skin</strong>{" "}
                    based on the product type.
                  </p>
                  <p className="inference-sub">Not your skin type? Re-analyze below:</p>
                </div>
              </div>
              <div className="inference-pills">
                {SKIN_TYPES.map((type) => (
                  <button
                    key={type}
                    className={`inf-pill${type === result.skin_type ? " active" : ""}`}
                    onClick={() => reAnalyze(type)}
                    disabled={loading}
                  >
                    {SKIN_TYPE_LABELS[type]}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* ── Product header ──────────────────────────────────────────── */}
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

          {/* ── Correction banner ───────────────────────────────────────── */}
          {result.corrected_name && (
            <div className="correction-banner">
              <span>✏️</span>
              <span>Analyzed as <strong>{result.corrected_name}</strong> (auto-corrected from &quot;{payload?.product_name}&quot;)</span>
            </div>
          )}

          {/* ── Ingredient source banners ─────────────────────────────── */}
          {result.ingredient_source === "obf_research" && (
            <div className="source-banner web-research-banner">
              <span>ℹ️</span>
              <span>Ingredients found from a similar product in our database — may not be an exact match. Upload a label photo for precise results.</span>
            </div>
          )}

          {(result.ingredient_source === "web_research" || result.ingredient_source === "estimated") && (
            <div className="source-banner estimated-banner">
              <span>⚠️</span>
              <span>Ingredients estimated based on product type — actual ingredients may differ. Upload a label photo for accurate analysis.</span>
            </div>
          )}

          {result.ingredient_source === "not_found" && (
            <div className="source-banner not-found-banner">
              <span>⚠️</span>
              <div>
                <p>We couldn&apos;t find the ingredient list for this product.</p>
                <button className="btn-upload-prompt" onClick={() => navigate("/")}>
                  📷 Upload a label photo for accurate analysis
                </button>
              </div>
            </div>
          )}

          {/* ── Score card ──────────────────────────────────────────────── */}
          <section className="score-card">
            <ScoreCircle score={result.suitability_score} />
            <div className="score-info">
              <p className="score-label-text" style={{ color: scoreColor(result.suitability_score) }}>
                {scoreLabel(result.suitability_score, result.skin_type)}
              </p>
              <p className="score-summary">{result.summary}</p>
            </div>
          </section>

          {/* ── Red flags ───────────────────────────────────────────────── */}
          {result.red_flags.length > 0 && (
            <section className="r-section">
              <h2 className="section-title">⚠️ Red Flags</h2>
              <div className="red-flags-list">
                {result.red_flags.map((flag, i) => (
                  <RedFlagAlert
                    key={i}
                    ingredient={flag.ingredient}
                    reason={flag.reason}
                    severity={flag.severity}
                  />
                ))}
              </div>
            </section>
          )}

          {/* ── Ingredient breakdown ────────────────────────────────────── */}
          {result.ingredients.length > 0 && (
            <IngredientsSection
              ingredients={result.ingredients}
              ingredientsFound={result.ingredients_found}
              ingredientSource={result.ingredient_source}
            />
          )}

          {/* ── Brand vs Reality ────────────────────────────────────────── */}
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

          {/* ── Section 5: Cheaper alternatives ─────────────────────────── */}
          <section className="r-section">
            <h2 className="section-title">💰 Cheaper Alternatives</h2>
            <p className="section-subtitle">
              Products with similar active ingredients at a lower price
            </p>
            <AlternativesGrid alternatives={alternatives} loading={altLoading} />
          </section>

          {/* ── Section 6: Routine compatibility ────────────────────────── */}
          {(payload?.second_product) && (
            <section className="r-section">
              <h2 className="section-title">🔄 Routine Compatibility</h2>
              <CompatibilityChecker
                result={compatibility}
                loading={compatLoading}
                product1={result.product_name}
                product2={payload.second_product}
              />
            </section>
          )}

          {/* ── Analyse another ─────────────────────────────────────────── */}
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

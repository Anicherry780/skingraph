import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { supabase } from "../lib/supabase";
import "./Dashboard.css";

// ── Types ────────────────────────────────────────────────────────────────────

type DashTab = "history" | "saved" | "profile";
type SkinTypeOption = "oily" | "dry" | "combination" | "sensitive";

interface AnalysisRow {
  id: string;
  product_name: string;
  skin_type: string;
  score: number;
  analysis_result: Record<string, unknown>;
  created_at: string;
}

interface SavedRow {
  id: string;
  product_name: string;
  skin_type: string;
  score: number;
  analysis_result: Record<string, unknown>;
  created_at: string;
}

interface ProfileData {
  skin_type: string | null;
  allergies: string[];
  concerns: string[];
}

const CONCERN_OPTIONS = [
  "Acne",
  "Aging",
  "Hyperpigmentation",
  "Sensitivity",
  "Dryness",
  "Redness",
  "Dark circles",
  "Large pores",
];

const SKIN_TYPES: SkinTypeOption[] = ["oily", "dry", "combination", "sensitive"];

const SKIN_TYPE_LABELS: Record<string, string> = {
  oily: "Oily",
  dry: "Dry",
  combination: "Combination",
  sensitive: "Sensitive",
};

// ── Helpers ──────────────────────────────────────────────────────────────────

function scoreColor(score: number) {
  if (score >= 70) return "var(--green)";
  if (score >= 40) return "var(--amber)";
  return "var(--red)";
}

function formatDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

// ── Component ────────────────────────────────────────────────────────────────

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { user, signOut } = useAuth();
  const [tab, setTab] = useState<DashTab>("history");

  // History state
  const [analyses, setAnalyses] = useState<AnalysisRow[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);

  // Saved state
  const [saved, setSaved] = useState<SavedRow[]>([]);
  const [savedLoading, setSavedLoading] = useState(true);

  // Profile state
  const [profile, setProfile] = useState<ProfileData>({
    skin_type: null,
    allergies: [],
    concerns: [],
  });
  const [allergiesText, setAllergiesText] = useState("");
  const [profileLoading, setProfileLoading] = useState(true);
  const [profileSaved, setProfileSaved] = useState(false);

  // ── Fetch data ─────────────────────────────────────────────────────────

  useEffect(() => {
    if (!user) return;

    // Fetch history
    supabase
      .from("user_analyses")
      .select("*")
      .eq("user_id", user.id)
      .order("created_at", { ascending: false })
      .then(({ data }) => {
        setAnalyses((data as AnalysisRow[]) ?? []);
        setHistoryLoading(false);
      });

    // Fetch saved
    supabase
      .from("user_saved_products")
      .select("*")
      .eq("user_id", user.id)
      .order("created_at", { ascending: false })
      .then(({ data }) => {
        setSaved((data as SavedRow[]) ?? []);
        setSavedLoading(false);
      });

    // Fetch profile
    supabase
      .from("user_profiles")
      .select("skin_type, allergies, concerns")
      .eq("id", user.id)
      .single()
      .then(({ data }) => {
        if (data) {
          const p = data as ProfileData;
          setProfile({
            skin_type: p.skin_type,
            allergies: p.allergies ?? [],
            concerns: p.concerns ?? [],
          });
          setAllergiesText((p.allergies ?? []).join(", "));
        }
        setProfileLoading(false);
      });
  }, [user]);

  // ── Handlers ───────────────────────────────────────────────────────────

  const handleViewAnalysis = (row: AnalysisRow) => {
    // Navigate to results with the saved analysis
    navigate("/results", {
      state: {
        payload: {
          product_name: row.product_name,
          skin_type: row.skin_type,
          skin_type_inferred: false,
        },
        preloadedResult: row.analysis_result,
      },
    });
  };

  const handleUnsave = async (id: string) => {
    await supabase.from("user_saved_products").delete().eq("id", id);
    setSaved((prev) => prev.filter((s) => s.id !== id));
  };

  const handleSaveProfile = async () => {
    if (!user) return;
    const allergiesArr = allergiesText
      .split(",")
      .map((a) => a.trim())
      .filter(Boolean);

    await supabase.from("user_profiles").upsert({
      id: user.id,
      skin_type: profile.skin_type,
      allergies: allergiesArr,
      concerns: profile.concerns,
    });

    setProfile((p) => ({ ...p, allergies: allergiesArr }));
    setProfileSaved(true);
    setTimeout(() => setProfileSaved(false), 2500);
  };

  const toggleConcern = (c: string) => {
    setProfile((p) => ({
      ...p,
      concerns: p.concerns.includes(c)
        ? p.concerns.filter((x) => x !== c)
        : [...p.concerns, c],
    }));
  };

  const handleSignOut = async () => {
    await signOut();
    navigate("/");
  };

  // ── Render ─────────────────────────────────────────────────────────────

  return (
    <div className="dash-container">
      {/* Header */}
      <header className="dash-header">
        <h1 className="dash-logo" onClick={() => navigate("/")}>
          Skin<span className="logo-green">Graph</span>
        </h1>
        <div className="dash-header-right">
          <span className="dash-email">{user?.email}</span>
          <button className="dash-signout" onClick={handleSignOut}>Sign out</button>
        </div>
      </header>

      {/* Tab bar */}
      <div className="dash-tabs">
        <button
          className={`dash-tab ${tab === "history" ? "active" : ""}`}
          onClick={() => setTab("history")}
        >
          📊 History
        </button>
        <button
          className={`dash-tab ${tab === "saved" ? "active" : ""}`}
          onClick={() => setTab("saved")}
        >
          🔖 Saved
        </button>
        <button
          className={`dash-tab ${tab === "profile" ? "active" : ""}`}
          onClick={() => setTab("profile")}
        >
          👤 Profile
        </button>
      </div>

      {/* Content */}
      <main className="dash-content">
        {/* ── History tab ────────────────────────────────────────────── */}
        {tab === "history" && (
          <section className="dash-section">
            <h2 className="dash-section-title">Analysis History</h2>
            {historyLoading ? (
              <p className="dash-empty">Loading...</p>
            ) : analyses.length === 0 ? (
              <div className="dash-empty-state">
                <span className="empty-icon">📊</span>
                <p>No analyses yet.</p>
                <button className="dash-cta" onClick={() => navigate("/")}>
                  Analyze your first product →
                </button>
              </div>
            ) : (
              <div className="dash-cards">
                {analyses.map((a) => (
                  <div key={a.id} className="dash-card" onClick={() => handleViewAnalysis(a)}>
                    <div className="dash-card-top">
                      <span className="dash-card-name">{a.product_name}</span>
                      <span
                        className="dash-card-score"
                        style={{ background: scoreColor(a.score), color: "#fff" }}
                      >
                        {a.score}
                      </span>
                    </div>
                    <div className="dash-card-bottom">
                      <span className="dash-card-skin">{SKIN_TYPE_LABELS[a.skin_type] ?? a.skin_type} skin</span>
                      <span className="dash-card-date">{formatDate(a.created_at)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {/* ── Saved tab ─────────────────────────────────────────────── */}
        {tab === "saved" && (
          <section className="dash-section">
            <h2 className="dash-section-title">Saved Products</h2>
            {savedLoading ? (
              <p className="dash-empty">Loading...</p>
            ) : saved.length === 0 ? (
              <div className="dash-empty-state">
                <span className="empty-icon">🔖</span>
                <p>No saved products.</p>
                <p className="empty-sub">Bookmark products from the results page to see them here.</p>
              </div>
            ) : (
              <div className="dash-cards">
                {saved.map((s) => (
                  <div key={s.id} className="dash-card">
                    <div className="dash-card-top">
                      <span className="dash-card-name">{s.product_name}</span>
                      <span
                        className="dash-card-score"
                        style={{ background: scoreColor(s.score), color: "#fff" }}
                      >
                        {s.score}
                      </span>
                    </div>
                    <div className="dash-card-bottom">
                      <span className="dash-card-skin">{SKIN_TYPE_LABELS[s.skin_type] ?? s.skin_type} skin</span>
                      <div className="dash-card-actions">
                        <span className="dash-card-date">{formatDate(s.created_at)}</span>
                        <button
                          className="dash-unsave-btn"
                          onClick={(e) => { e.stopPropagation(); handleUnsave(s.id); }}
                        >
                          ✕ Remove
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {/* ── Profile tab ───────────────────────────────────────────── */}
        {tab === "profile" && (
          <section className="dash-section">
            <h2 className="dash-section-title">Skin Profile</h2>
            {profileLoading ? (
              <p className="dash-empty">Loading...</p>
            ) : (
              <div className="dash-profile-form">
                {/* Skin type */}
                <div className="profile-field">
                  <label className="profile-label">Skin Type</label>
                  <div className="profile-pills">
                    {SKIN_TYPES.map((t) => (
                      <button
                        key={t}
                        className={`profile-pill ${profile.skin_type === t ? "selected" : ""}`}
                        onClick={() => setProfile((p) => ({ ...p, skin_type: t }))}
                      >
                        {SKIN_TYPE_LABELS[t]}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Allergies */}
                <div className="profile-field">
                  <label className="profile-label" htmlFor="allergies-input">
                    Known Allergies
                  </label>
                  <input
                    id="allergies-input"
                    type="text"
                    className="profile-input"
                    value={allergiesText}
                    onChange={(e) => setAllergiesText(e.target.value)}
                    placeholder="e.g. Fragrance, Parabens, Silicone"
                  />
                  <span className="profile-hint">Separate with commas</span>
                </div>

                {/* Concerns */}
                <div className="profile-field">
                  <label className="profile-label">Skin Concerns</label>
                  <div className="profile-pills">
                    {CONCERN_OPTIONS.map((c) => (
                      <button
                        key={c}
                        className={`profile-pill ${profile.concerns.includes(c) ? "selected" : ""}`}
                        onClick={() => toggleConcern(c)}
                      >
                        {c}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Save */}
                <button className="profile-save" onClick={handleSaveProfile}>
                  Save Profile
                </button>
                {profileSaved && (
                  <p className="profile-success">✓ Profile saved successfully</p>
                )}
              </div>
            )}
          </section>
        )}
      </main>

      {/* Analyze CTA */}
      <div className="dash-footer-cta">
        <button className="dash-cta" onClick={() => navigate("/")}>
          ← Analyze a product
        </button>
      </div>
    </div>
  );
};

export default Dashboard;

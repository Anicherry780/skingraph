import React from "react";
import { useLocation, useNavigate } from "react-router-dom";
import "./Results.css";

// Phase 2 placeholder — full analysis UI built in Phase 2
const Results: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const payload = location.state?.payload;

  return (
    <div className="results-container">
      <header className="results-header">
        <button className="back-btn" onClick={() => navigate(-1)}>
          ← Back
        </button>
        <h1 className="logo">
          Skin<span className="logo-green">Graph</span>
        </h1>
      </header>

      <main className="results-main">
        <div className="results-placeholder">
          <div className="placeholder-icon">🔬</div>
          <h2>Analysis coming in Phase 2</h2>
          <p>
            Product: <strong>{payload?.product_name || "—"}</strong>
          </p>
          <p>
            Skin type:{" "}
            <strong>
              {payload?.skin_type || "—"}
              {payload?.skin_type_inferred ? " (auto-inferred)" : ""}
            </strong>
          </p>
          {payload?.second_product && (
            <p>
              Checking compatibility with: <strong>{payload.second_product}</strong>
            </p>
          )}
          <p className="placeholder-note">
            The backend pipeline (Nova Act + Nova 2 Lite) will be wired up in Phase 2.
          </p>
        </div>
      </main>
    </div>
  );
};

export default Results;

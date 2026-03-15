import React from "react";
import "./RedFlagAlert.css";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface RedFlagAlertProps {
  ingredient: string;
  reason: string;
  severity: "low" | "medium" | "high";
}

// ── Component ─────────────────────────────────────────────────────────────────

const RedFlagAlert: React.FC<RedFlagAlertProps> = ({ ingredient, reason, severity }) => {
  return (
    <div className={`red-flag-card sev-${severity}`}>
      <div className="flag-top">
        <span className="flag-name">{ingredient}</span>
        <span className={`sev-badge sev-${severity}`}>{severity}</span>
      </div>
      <p className="flag-reason">{reason}</p>
    </div>
  );
};

export default RedFlagAlert;

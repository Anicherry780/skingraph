import React from "react";
import "./SkinTypeSelector.css";

type SkinTypeOption = "oily" | "dry" | "combination" | "sensitive";

interface SkinTypeSelectorProps {
  selected: SkinTypeOption | null;
  inferred: boolean;
  inferredReason: string;
  matchedKeyword: string;
  onChange: (type: SkinTypeOption, manual: boolean) => void;
}

const SKIN_TYPE_LABELS: Record<SkinTypeOption, string> = {
  oily: "Oily",
  dry: "Dry",
  combination: "Combination",
  sensitive: "Sensitive",
};

const SkinTypeSelector: React.FC<SkinTypeSelectorProps> = ({
  selected,
  inferred,
  inferredReason,
  matchedKeyword,
  onChange,
}) => {
  const types: SkinTypeOption[] = ["oily", "dry", "combination", "sensitive"];

  return (
    <div className="skin-type-selector">
      <label className="skin-type-label">Skin type</label>
      <div className="skin-type-pills">
        {types.map((type) => {
          const isSelected = selected === type;
          const isAuto = isSelected && inferred;
          return (
            <button
              key={type}
              type="button"
              className={`pill ${isSelected ? "selected" : ""} ${isAuto ? "auto" : ""}`}
              onClick={() => onChange(type, true)}
              aria-pressed={isSelected}
            >
              {SKIN_TYPE_LABELS[type]}
              {isAuto && <span className="auto-badge">auto</span>}
            </button>
          );
        })}
      </div>

      {inferred && selected && matchedKeyword && (
        <p className="inference-hint">
          Based on &ldquo;<strong>{matchedKeyword}</strong>&rdquo; we&apos;ve assumed{" "}
          <strong>{SKIN_TYPE_LABELS[selected]} skin</strong> — tap to change
        </p>
      )}

      {!inferred && inferredReason && (
        <p className="inference-reason">{inferredReason}</p>
      )}
    </div>
  );
};

export default SkinTypeSelector;

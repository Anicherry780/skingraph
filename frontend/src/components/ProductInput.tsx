import React from "react";
import { inferSkinType } from "../utils/inferSkinType";
import type { InferenceResult } from "../utils/inferSkinType";
import "./ProductInput.css";

interface ProductInputProps {
  value: string;
  placeholder?: string;
  onChange: (value: string, inference: InferenceResult) => void;
  disabled?: boolean;
}

const ProductInput: React.FC<ProductInputProps> = ({
  value,
  placeholder = "e.g. CeraVe Moisturising Cream",
  onChange,
  disabled = false,
}) => {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    const inference = inferSkinType(newValue);
    onChange(newValue, inference);
  };

  return (
    <div className="product-input-wrapper">
      <input
        type="text"
        className="product-input"
        value={value}
        onChange={handleChange}
        placeholder={placeholder}
        disabled={disabled}
        autoComplete="off"
        spellCheck={false}
      />
      <p className="product-input-hint">We&apos;ll find the ingredient list live</p>
    </div>
  );
};

export default ProductInput;

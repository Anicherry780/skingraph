import React, { useState, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import ProductInput from "../components/ProductInput";
import SkinTypeSelector from "../components/SkinTypeSelector";
import type { InferenceResult } from "../utils/inferSkinType";
import "./Home.css";

type SkinTypeOption = "oily" | "dry" | "combination" | "sensitive";

interface AnalyzePayload {
  product_name: string;
  skin_type: string;
  skin_type_inferred: boolean;
  second_product?: string;
  image_base64?: string;
}

const Home: React.FC = () => {
  const navigate = useNavigate();

  // Primary product state
  const [productName, setProductName] = useState("");
  const [selectedSkinType, setSelectedSkinType] = useState<SkinTypeOption | null>(null);
  const [isInferred, setIsInferred] = useState(false);
  const [inferredReason, setInferredReason] = useState("");
  const [matchedKeyword, setMatchedKeyword] = useState("");

  // Second product state
  const [showSecondProduct, setShowSecondProduct] = useState(false);
  const [secondProductName, setSecondProductName] = useState("");

  // Photo upload state
  const [uploadedImage, setUploadedImage] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Loading state
  const [isLoading, setIsLoading] = useState(false);

  // Analyze button enabled when product typed AND skin type selected
  const canAnalyze = productName.trim().length > 0 && selectedSkinType !== null;

  // Handle product input change — runs inferSkinType on every keystroke
  const handleProductChange = useCallback(
    (value: string, inference: InferenceResult) => {
      setProductName(value);

      if (value.trim() === "") {
        // Clear all state when input is cleared
        setSelectedSkinType(null);
        setIsInferred(false);
        setInferredReason("");
        setMatchedKeyword("");
        return;
      }

      if (inference.skinType) {
        setSelectedSkinType(inference.skinType as SkinTypeOption);
        setIsInferred(true);
        setInferredReason(inference.reason);
        setMatchedKeyword(inference.matchedKeyword);
      } else {
        // If no match found, keep current manual selection (don't reset it)
        if (isInferred) {
          setSelectedSkinType(null);
          setIsInferred(false);
          setInferredReason("");
          setMatchedKeyword("");
        }
      }
    },
    [isInferred]
  );

  // Handle skin type pill click — manual override clears auto badge
  const handleSkinTypeChange = (type: SkinTypeOption, manual: boolean) => {
    setSelectedSkinType(type);
    if (manual) {
      setIsInferred(false);
      setMatchedKeyword("");
    }
  };

  // Handle second product input
  const handleSecondProductChange = (_value: string, _inference: InferenceResult) => {
    setSecondProductName(_value);
  };

  // Handle file upload
  const processFile = (file: File) => {
    if (!file.type.match(/^image\/(jpeg|png|webp)$/)) {
      alert("Please upload a JPG, PNG, or WEBP image.");
      return;
    }
    const reader = new FileReader();
    reader.onload = (e) => {
      const base64 = (e.target?.result as string).split(",")[1];
      setUploadedImage(base64);

      // If no skin type inferred yet, hint user it'll come from label
      if (!selectedSkinType) {
        setInferredReason("Skin type will be detected from the label");
      }
    };
    reader.readAsDataURL(file);
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) processFile(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => setIsDragOver(false);

  // Submit handler
  const handleAnalyze = async () => {
    if (!canAnalyze) return;
    setIsLoading(true);

    const payload: AnalyzePayload = {
      product_name: productName,
      skin_type: selectedSkinType ?? "auto",
      skin_type_inferred: isInferred,
    };

    if (showSecondProduct && secondProductName.trim()) {
      payload.second_product = secondProductName;
    }

    if (uploadedImage) {
      payload.image_base64 = uploadedImage;
    }

    // Navigate to results page with payload in state
    // Backend integration happens in Phase 2
    navigate("/results", { state: { payload } });
  };

  return (
    <div className="home-container">
      {/* Header */}
      <header className="home-header">
        <h1 className="logo">
          Skin<span className="logo-green">Graph</span>
        </h1>
        <p className="tagline">Know exactly what&apos;s in your skincare</p>
        <span className="nova-badge">Powered by Amazon Nova</span>
      </header>

      {/* Main form */}
      <main className="home-main">
        <div className="form-card">
          {/* Product name input */}
          <section className="form-section">
            <label className="section-label">Product name</label>
            <ProductInput
              value={productName}
              onChange={handleProductChange}
              disabled={isLoading}
            />
          </section>

          {/* Skin type selector */}
          <section className="form-section">
            <SkinTypeSelector
              selected={selectedSkinType}
              inferred={isInferred}
              inferredReason={inferredReason}
              matchedKeyword={matchedKeyword}
              onChange={handleSkinTypeChange}
            />
          </section>

          {/* Photo upload — optional */}
          <section className="form-section">
            <div className="upload-label-row">
              <label className="section-label">Upload product label photo</label>
              <span className="optional-badge">OPTIONAL</span>
            </div>
            <div
              className={`drop-zone ${isDragOver ? "drag-over" : ""} ${uploadedImage ? "has-file" : ""}`}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => fileInputRef.current?.click()}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === "Enter" && fileInputRef.current?.click()}
            >
              {uploadedImage ? (
                <div className="upload-preview">
                  <span className="upload-check">✓</span>
                  <span>Label photo uploaded</span>
                  <button
                    className="remove-image"
                    onClick={(e) => {
                      e.stopPropagation();
                      setUploadedImage(null);
                    }}
                    type="button"
                  >
                    ✕
                  </button>
                </div>
              ) : (
                <div className="upload-prompt">
                  <span className="upload-icon">📷</span>
                  <span>Or upload a product label photo</span>
                  <span className="upload-types">JPG · PNG · WEBP</span>
                </div>
              )}
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={handleFileInput}
              style={{ display: "none" }}
            />
            {uploadedImage && !selectedSkinType && (
              <p className="upload-hint">Skin type will be detected from the label</p>
            )}
            <p className="upload-privacy">
              🔒 Uploaded photos are automatically deleted within 24 hours.
            </p>
          </section>

          {/* Routine compatibility toggle — optional */}
          <section className="form-section">
            <div className="compatibility-toggle-row">
              <label className="toggle-label" htmlFor="compat-toggle">
                Check routine compatibility?
              </label>
              <button
                id="compat-toggle"
                type="button"
                role="switch"
                aria-checked={showSecondProduct}
                className={`toggle-switch ${showSecondProduct ? "on" : "off"}`}
                onClick={() => setShowSecondProduct((v) => !v)}
              >
                <span className="toggle-thumb" />
              </button>
            </div>

            {showSecondProduct && (
              <div className="second-product-wrapper">
                <label className="section-label secondary">
                  Enter a second product to check if they&apos;re safe to use together
                </label>
                <ProductInput
                  value={secondProductName}
                  placeholder="e.g. The Ordinary Retinol 0.5%"
                  onChange={handleSecondProductChange}
                  disabled={isLoading}
                />
              </div>
            )}
          </section>

          {/* Analyze button */}
          <button
            type="button"
            className={`analyze-btn ${!canAnalyze ? "disabled" : ""} ${isLoading ? "loading" : ""}`}
            onClick={handleAnalyze}
            disabled={!canAnalyze || isLoading}
          >
            {isLoading ? (
              <>
                <span className="spinner" />
                Researching live...
              </>
            ) : canAnalyze ? (
              "Analyze ingredients →"
            ) : (
              "Enter a product to start"
            )}
          </button>
        </div>
      </main>

      {/* Footer */}
      <footer className="home-footer">
        <p>Not medical advice. Always patch test. Consult a dermatologist for skin conditions.</p>
      </footer>
    </div>
  );
};

export default Home;

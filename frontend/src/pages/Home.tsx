import React, { useEffect, useRef, useCallback, useState } from "react";
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

  // Camera
  const [cameraActive, setCameraActive] = useState(false);
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);

  // Label scan
  const [isScanning, setIsScanning] = useState(false);
  const [detectedInfo, setDetectedInfo] = useState<{
    product_name: string;
    skin_type_hint: string | null;
    labels: string[];
  } | null>(null);

  // Follow-up clarification
  const [followUp, setFollowUp] = useState<{ question: string; options: string[] } | null>(null);
  const [selectedFollowUp, setSelectedFollowUp] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Analyze button enabled when product typed AND skin type selected
  const canAnalyze = productName.trim().length > 0 && selectedSkinType !== null;

  // Follow-up question logic
  const getFollowUp = (name: string) => {
    const n = name.toLowerCase();
    if (/moisturis|moisturiz|cream/.test(n))
      return { question: "What texture is it?", options: ["Gel", "Cream", "Lotion"] };
    if (/sunscreen|sunblock|spf/.test(n))
      return { question: "What is the SPF level?", options: ["SPF 15", "SPF 30", "SPF 50", "SPF 50+"] };
    if (/\bserum\b/.test(n))
      return { question: "What type of serum?", options: ["Hydrating", "Treatment", "Vitamin C", "Retinol"] };
    return null;
  };

  // Handle product input change — runs inferSkinType on every keystroke
  const handleProductChange = useCallback(
    (value: string, inference: InferenceResult) => {
      setProductName(value);
      setFollowUp(getFollowUp(value));
      setSelectedFollowUp(null);

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
    [isInferred] // eslint-disable-line react-hooks/exhaustive-deps
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

  // scanLabel: call /api/scan-label with a base64 image
  const scanLabel = useCallback(async (base64: string) => {
    setIsScanning(true);
    setDetectedInfo(null);
    try {
      const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
      const resp = await fetch(`${apiUrl}/api/scan-label`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_base64: base64 }),
      });
      if (resp.ok) {
        const data = await resp.json();
        if (data.product_name && !productName.trim()) {
          setProductName(data.product_name);
          setFollowUp(getFollowUp(data.product_name));
          setSelectedFollowUp(null);
        }
        if (data.skin_type_hint && !isInferred) {
          setSelectedSkinType(data.skin_type_hint as SkinTypeOption);
          setIsInferred(true);
          setInferredReason("Detected from label photo");
          setMatchedKeyword("");
        }
        setDetectedInfo({
          product_name: data.product_name || "",
          skin_type_hint: data.skin_type_hint,
          labels: data.detected_labels || [],
        });
      }
    } catch {
      // silent fail — user can type manually
    } finally {
      setIsScanning(false);
    }
  }, [productName, isInferred]); // eslint-disable-line react-hooks/exhaustive-deps

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
      scanLabel(base64);

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

  // Camera functions
  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 } },
      });
      setCameraStream(stream);
      setCameraActive(true);
    } catch {
      alert("Camera unavailable. Please upload a photo instead.");
    }
  }, []);

  const stopCamera = useCallback(() => {
    cameraStream?.getTracks().forEach((t) => t.stop());
    setCameraStream(null);
    setCameraActive(false);
  }, [cameraStream]);

  const capturePhoto = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d")?.drawImage(video, 0, 0);
    const base64 = canvas.toDataURL("image/jpeg", 0.85).split(",")[1];
    setUploadedImage(base64);
    stopCamera();
    scanLabel(base64);
  }, [stopCamera, scanLabel]);

  // Camera stream setup
  useEffect(() => {
    if (cameraActive && cameraStream && videoRef.current) {
      videoRef.current.srcObject = cameraStream;
      videoRef.current.play().catch(() => {});
    }
  }, [cameraActive, cameraStream]);

  // Cleanup on unmount
  useEffect(() => {
    return () => { cameraStream?.getTracks().forEach((t) => t.stop()); };
  }, [cameraStream]);

  // Submit handler
  const handleAnalyze = async () => {
    if (!canAnalyze) return;
    setIsLoading(true);

    const finalProductName = selectedFollowUp
      ? `${productName} (${selectedFollowUp})`
      : productName;

    const payload: AnalyzePayload = {
      product_name: finalProductName,
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

          {/* Follow-up clarification pills */}
          {followUp && (
            <section className="form-section follow-up-section">
              <label className="section-label secondary">{followUp.question}</label>
              <div className="follow-up-pills">
                {followUp.options.map((opt) => (
                  <button
                    key={opt}
                    type="button"
                    className={`follow-up-pill ${selectedFollowUp === opt ? "selected" : ""}`}
                    onClick={() => setSelectedFollowUp(selectedFollowUp === opt ? null : opt)}
                  >
                    {opt}
                  </button>
                ))}
              </div>
            </section>
          )}

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

            {cameraActive ? (
              <>
                <div className="camera-preview-wrap">
                  <video ref={videoRef} autoPlay playsInline muted />
                </div>
                <div className="camera-controls">
                  <button type="button" className="capture-btn" onClick={capturePhoto}>
                    📸 Capture
                  </button>
                  <button type="button" className="cancel-camera-btn" onClick={stopCamera}>
                    ✕ Cancel
                  </button>
                </div>
              </>
            ) : (
              <>
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
                          setDetectedInfo(null);
                        }}
                        type="button"
                      >
                        ✕
                      </button>
                    </div>
                  ) : (
                    <div className="upload-prompt">
                      <span className="upload-icon">📷</span>
                      <span>Or drag &amp; drop a product label photo</span>
                      <span className="upload-types">JPG · PNG · WEBP</span>
                    </div>
                  )}
                </div>
                <div className="upload-actions">
                  <button
                    type="button"
                    className="upload-action-btn"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    📁 Upload Photo
                  </button>
                  <button
                    type="button"
                    className="upload-action-btn"
                    onClick={startCamera}
                  >
                    📷 Use Camera
                  </button>
                </div>
              </>
            )}

            <canvas ref={canvasRef} style={{ display: "none" }} />

            {isScanning && (
              <p className="scanning-label">🔍 Reading label...</p>
            )}

            {detectedInfo && detectedInfo.labels.length > 0 && (
              <div className="detection-banner">
                <span className="detection-icon">🔬</span>
                <span>Detected: {detectedInfo.labels.slice(0, 3).join(" · ")}</span>
              </div>
            )}

            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={handleFileInput}
              style={{ display: "none" }}
            />
            {uploadedImage && !selectedSkinType && !isScanning && (
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

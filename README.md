# SkinGraph

**Live URL:** https://skin.anirudhdev.com
**Hackathon:** Amazon Nova AI Hackathon — March 16–17, 2026

> Know exactly what's in your skincare. SkinGraph analyzes every ingredient, flags irritants for your skin type, and finds cheaper alternatives — all powered by Amazon Nova.

---

## What it does

1. User types a skincare product name (or uploads a label photo)
2. Site **automatically pre-selects the skin type** from the product name in real time (zero API cost)
3. User can override the pre-selected skin type
4. Nova Act navigates INCI Decoder, Amazon, and brand product pages simultaneously via AWS Lambda parallel sessions
5. Nova 2 Lite analyzes every ingredient against the user's skin type in a single 1M context pass
6. Nova Embeddings finds cheaper alternatives with 85%+ ingredient match

---

## Stack

| Layer | Tech |
|-------|------|
| Frontend | React + Vite + TypeScript → Cloudflare Pages |
| Backend | FastAPI → Railway |
| AI | Amazon Nova Act · Nova 2 Lite · Nova Embeddings |
| Infra | AWS Lambda (parallel sessions) · Amazon Textract (OCR) |
| DB | Supabase (pgvector for embedding cache) |

---

## Nova model roles

**Nova Act** — Opens a real Chrome browser. Navigates INCI Decoder, Amazon, and brand product pages live — all three simultaneously via AWS Lambda parallel invocations.

**Nova 2 Lite** — Reads all collected ingredient data in one 1M context pass. Classifies every ingredient, assesses risk for the user's skin type, and gives an honest assessment vs brand claims.

**Nova Embeddings** — Converts ingredient lists to semantic vectors. Finds cheaper alternatives with 85%+ ingredient match even when ingredient names differ across brands.

---

## ETL Pipeline

```
Extract  →  Nova Act (3 parallel Lambda sessions scraping live web)
Transform →  Nova 2 Lite (ingredient classification + risk analysis)
Load     →  Supabase (results cached with Nova Embeddings for reuse)
```

---

## Pre-assumption logic

The site automatically infers skin type from the product name — no API call needed:

| Keyword | Inferred type |
|---------|--------------|
| "moisturizer", "moisturising", "hydrating" | Dry |
| "niacinamide", "salicylic acid", "matte", "clay" | Oily |
| "centella", "cica", "soothing", "barrier" | Sensitive |
| "water gel", "serum", "gel", "retinol" | Combination |

---

## Local development

### Frontend
```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload
```

---

## Build phases

- **Phase 1** ✅ — Scaffold + input screen + skin type pre-assumption UI
- **Phase 2** — Nova pipeline + backend analysis endpoint
- **Phase 3** — Nova Embeddings: alternatives + routine compatibility
- **Phase 4** — Textract photo upload
- **Phase 5** — UI polish + demo prep

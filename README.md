# SkinGraph

Know exactly what's in your skincare.

**Live:** https://skin.anirudhdev.com
**Hackathon:** Amazon Nova AI Hackathon — March 2026

## What it does

Upload a product label photo OR type a product name → SkinGraph extracts every ingredient, analyzes safety for your skin type, flags irritants, and finds cheaper alternatives — all powered by Amazon Nova.

## AWS Services

- **Amazon Bedrock** — Nova 2 Lite (ingredient analysis), Nova Embeddings (semantic cache), Nova Act (brand claims)
- **Amazon S3** — stores uploaded photos (auto-deleted after 24hrs) and analysis reports permanently
- **Amazon Textract** — OCR extracts ingredient lists from uploaded product label photos
- **Amazon Rekognition** — CV detects product type from photos to auto-fill product name and skin type

## Stack

| Layer | Tech |
|---|---|
| Frontend | React + Vite + TypeScript → Cloudflare Pages |
| Backend | FastAPI (Python 3.11) → Render |
| AI | Amazon Bedrock (Nova 2 Lite + Embeddings + Act) |
| CV/OCR | Amazon Rekognition + Textract |
| Storage | Amazon S3 + Supabase (pgvector) |

## ETL Pipeline

```
Extract → Open Beauty Facts API (ingredients) +
          Textract (photo OCR) +
          Rekognition (CV product detection) +
          Nova Act (brand claims)
Transform → Nova 2 Lite (ingredient classification +
            risk analysis per skin type)
Load → Supabase pgvector cache + S3 analysis reports
```

## Pre-assumption logic

Site auto-infers skin type from product name in real time. No API call needed. Zero cost.

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

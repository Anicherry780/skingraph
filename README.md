# SkinGraph 🧴

> Know exactly what's in your skincare — powered by Amazon Nova.

**🌐 Live:** [skin.anirudhdev.com](https://skin.anirudhdev.com)  
**📱 Android:** APK built with Capacitor (loads production site)  
**🏆 Hackathon:** Amazon Nova AI Hackathon — March 2026

---

## What it does

Type a product name or upload a label photo → SkinGraph extracts every ingredient, scores suitability for your skin type, flags irritants, finds cheaper alternatives, and checks routine compatibility — all in real time.

**With a free account, it also:**
- Saves every analysis to your history
- Bookmarks products you want to revisit
- Remembers your skin type, allergies, and concerns
- Pre-fills your skin type on every new analysis

---

## AWS Services

| Service | Use |
|---|---|
| **Amazon Bedrock — Nova 2 Lite** | Ingredient classification + risk analysis per skin type |
| **Amazon Bedrock — Nova Embeddings** | Semantic cache (avoid re-analyzing the same product twice) |
| **Amazon Nova Act** | Brand vs reality — validates marketing claims against science |
| **Amazon Textract** | OCR — extracts ingredient lists from uploaded label photos |
| **Amazon Rekognition** | CV — detects product name and type from label photos |
| **Amazon S3** | Stores uploaded photos (auto-deleted 24hrs) + analysis reports |

---

## Stack

| Layer | Tech |
|---|---|
| Frontend | React 19 + TypeScript + Vite → Cloudflare Pages |
| Backend | FastAPI (Python 3.12) → Render |
| Auth & DB | Supabase (Auth + Postgres + pgvector) |
| AI | Amazon Bedrock (Nova 2 Lite + Embeddings + Act) |
| CV / OCR | Amazon Rekognition + Textract |
| Storage | Amazon S3 |
| Android | Capacitor (WebView wrapper) |

---

## Architecture

```
User (Web / Android)
        ↓
React + Vite frontend (Cloudflare Pages)
        ↓
FastAPI backend (Render)
    ├── Supabase pgvector → semantic cache check
    │       ↓ cache miss
    ├── Open Beauty Facts API → ingredient list
    │   OR Amazon Textract → OCR from label photo
    ├── Amazon Rekognition → detect product from photo
    ├── Amazon Nova 2 Lite → analyze + score ingredients
    ├── Amazon Nova Act → verify brand claims
    └── S3 → store photo + report
        ↓
User dashboard (Supabase Auth + Postgres)
    ├── Analysis history
    ├── Saved/bookmarked products
    └── Skin profile (type, allergies, concerns)
```

---

## Database schema

```sql
-- User skin profile
user_profiles (id, skin_type, allergies[], concerns[])

-- Every analysis a user runs
user_analyses (id, user_id, product_name, skin_type, score, analysis_result jsonb)

-- Products a user bookmarks
user_saved_products (id, user_id, product_name, skin_type, score, analysis_result jsonb)
```

Row Level Security enabled on all tables — users only see their own data.

---

## Features

- ✅ Product name → live ingredient analysis
- ✅ Label photo upload (up to 5 photos) → OCR ingredient extraction
- ✅ Camera scan directly in app
- ✅ Auto skin type inference from product name
- ✅ Suitability score (0–100) with animated circle
- ✅ Ingredient breakdown with comedogenic ratings + irritant risk
- ✅ Red flag alerts
- ✅ Brand claims vs science check
- ✅ Cheaper alternative products
- ✅ Two-product routine compatibility check
- ✅ User accounts (email + Google OAuth)
- ✅ Analysis history + saved products + skin profile
- ✅ Android app (Capacitor)

---

## Local development

### Prerequisites
- Node 18+ and npm
- Python 3.12
- Supabase project
- AWS account with Bedrock, Textract, Rekognition, S3 access

### Frontend
```bash
cd frontend
npm install
cp .env.example .env
# Fill in VITE_API_URL, VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY
npm run dev
```

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate     # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill in AWS, Supabase, and other keys
uvicorn main:app --reload
```

### Android (after running frontend build)
```bash
cd frontend
npm run cap:sync          # builds web + syncs to Android project
npx cap open android      # opens Android Studio
```

---

## Environment variables

### Frontend (`frontend/.env`)
```
VITE_API_URL=https://skingraph-backend.onrender.com
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

### Backend (`backend/.env`)
```
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET_NAME=...
SUPABASE_URL=...
SUPABASE_SERVICE_KEY=...
```

---

## License

MIT

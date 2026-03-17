from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging
import os

load_dotenv()

# Ensure all our loggers output at INFO level (Render may default to WARNING)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("services").setLevel(logging.INFO)
logging.getLogger("routes").setLevel(logging.INFO)

app = FastAPI(title="SkinGraph API", version="2.0.0")

# CORS — allow Cloudflare Pages frontend and local dev
origins = [
    "https://skin.anirudhdev.com",
    "https://skingraph.pages.dev",
    "http://localhost:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ──────────────────────────────────────────────────────────────────
from routes.analyze import router as analyze_router
from routes.alternatives import router as alternatives_router
from routes.compatibility import router as compatibility_router

from routes.scan_label import router as scan_label_router
from routes.email import router as email_router

app.include_router(analyze_router)
app.include_router(alternatives_router)
app.include_router(compatibility_router)
app.include_router(scan_label_router)
app.include_router(email_router)

@app.get("/")
async def root():
    return {"status": "ok", "service": "SkinGraph API", "phase": 4}

@app.get("/health")
async def health():
    return {"status": "healthy"}


# ── Diagnostic endpoints (Phase 4 debugging) ────────────────────────────────

@app.get("/api/test-s3")
async def test_s3():
    """Upload a small test file to S3 and verify connectivity."""
    from services.s3_service import test_s3_connection
    return test_s3_connection()


@app.get("/api/debug-env")
async def debug_env():
    """Check which AWS env vars are set (no values exposed)."""
    return {
        "AWS_REGION": os.getenv("AWS_REGION", "(not set, default us-east-1)"),
        "AWS_ACCESS_KEY_ID": "set" if os.getenv("AWS_ACCESS_KEY_ID") else "NOT SET",
        "AWS_SECRET_ACCESS_KEY": "set" if os.getenv("AWS_SECRET_ACCESS_KEY") else "NOT SET",
        "SUPABASE_URL": "set" if os.getenv("SUPABASE_URL") else "NOT SET",
    }

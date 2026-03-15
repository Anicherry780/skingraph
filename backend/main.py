from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

load_dotenv()

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

app.include_router(analyze_router)
app.include_router(alternatives_router)
app.include_router(compatibility_router)

# Phase 4+
# from routes.upload import router as upload_router


@app.get("/")
async def root():
    return {"status": "ok", "service": "SkinGraph API", "phase": 3}

@app.get("/health")
async def health():
    return {"status": "healthy"}

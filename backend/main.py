from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(title="SkinGraph API", version="1.0.0")

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

# Import routes — Phase 2+ will add analyze, alternatives, compatibility, upload
# from routes.analyze import router as analyze_router
# app.include_router(analyze_router)

@app.get("/")
async def root():
    return {"status": "ok", "service": "SkinGraph API", "phase": 1}

@app.get("/health")
async def health():
    return {"status": "healthy"}

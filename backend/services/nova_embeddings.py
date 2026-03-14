"""
Nova Embeddings + Supabase cache.

Phase 2: Simple deterministic cache key (SHA-256 of product_name + skin_type).
Phase 3: Will add vector similarity search for alternatives matching.

Supabase table required:
    CREATE TABLE product_analyses (
        id          uuid DEFAULT gen_random_uuid() PRIMARY KEY,
        cache_key   text UNIQUE NOT NULL,
        product_name text NOT NULL,
        skin_type   text NOT NULL,
        analysis_result jsonb NOT NULL,
        created_at  timestamptz DEFAULT now()
    );
"""

import hashlib
import json
import logging
import os
from typing import Optional

import boto3

logger = logging.getLogger(__name__)

TITAN_EMBED_MODEL = "amazon.titan-embed-text-v2:0"


# ── Supabase helpers ────────────────────────────────────────────────────────

def _get_supabase():
    """Return Supabase client, or None if not configured."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        logger.warning("Supabase not configured — cache disabled")
        return None
    try:
        from supabase import create_client
        return create_client(url, key)
    except Exception as e:
        logger.error(f"Supabase client error: {e}")
        return None


def _cache_key(product_name: str, skin_type: str) -> str:
    """Deterministic 16-char cache key from product + skin type."""
    normalized = f"{product_name.strip().lower()}::{skin_type.strip().lower()}"
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


# ── Embedding generation (for Phase 3 similarity search) ───────────────────

def generate_embedding(text: str) -> Optional[list]:
    """
    Generate a text embedding using Amazon Titan Embed Text v2.
    Used in Phase 3 for finding alternative products via cosine similarity.
    """
    try:
        client = boto3.client(
            "bedrock-runtime",
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
        body = json.dumps({"inputText": text[:8000]})  # Titan has 8k token limit
        response = client.invoke_model(
            modelId=TITAN_EMBED_MODEL,
            body=body,
            contentType="application/json",
            accept="application/json",
        )
        result = json.loads(response["body"].read())
        return result.get("embedding")
    except Exception as e:
        logger.error(f"Embedding generation error: {e}")
        return None


# ── Cache read / write ──────────────────────────────────────────────────────

def check_cache(product_name: str, skin_type: str) -> Optional[dict]:
    """
    Check Supabase for a previously computed analysis.
    Returns the analysis dict with "cached": True if found, else None.
    """
    db = _get_supabase()
    if not db:
        return None

    try:
        key = _cache_key(product_name, skin_type)
        result = (
            db.table("product_analyses")
            .select("analysis_result")
            .eq("cache_key", key)
            .limit(1)
            .execute()
        )

        if result.data:
            logger.info(f"Cache hit: {product_name} / {skin_type}")
            cached = result.data[0]["analysis_result"]
            # Supabase returns jsonb as dict already; guard against string
            if isinstance(cached, str):
                cached = json.loads(cached)
            cached["cached"] = True
            return cached

        return None

    except Exception as e:
        logger.error(f"Cache read error: {e}")
        return None


def save_to_cache(product_name: str, skin_type: str, analysis: dict) -> None:
    """
    Persist analysis result to Supabase.
    Upserts on cache_key so re-runs update stale entries.
    """
    db = _get_supabase()
    if not db:
        return

    try:
        key = _cache_key(product_name, skin_type)
        # Don't cache error responses
        if analysis.get("error"):
            return

        db.table("product_analyses").upsert(
            {
                "cache_key": key,
                "product_name": product_name,
                "skin_type": skin_type,
                "analysis_result": analysis,
            },
            on_conflict="cache_key",
        ).execute()

        logger.info(f"Cached: {product_name} / {skin_type}")

    except Exception as e:
        logger.error(f"Cache write error: {e}")

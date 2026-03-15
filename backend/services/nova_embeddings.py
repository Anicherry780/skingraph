"""
Nova Embeddings + Supabase vector cache.

Cache strategy: cosine similarity via pgvector (threshold 0.92).
Falls back to exact hash match if embedding unavailable.

Supabase setup — run once in SQL editor:
─────────────────────────────────────────────────────────────────
-- 1. Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create (or recreate) table with embedding column
CREATE TABLE IF NOT EXISTS product_analyses (
    id               uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    cache_key        text UNIQUE NOT NULL,
    product_name     text NOT NULL,
    skin_type        text NOT NULL,
    analysis_result  jsonb NOT NULL,
    embedding        vector(1024),
    created_at       timestamptz DEFAULT now()
);

-- 3. Vector similarity search function
CREATE OR REPLACE FUNCTION match_product_analyses(
    query_embedding  vector(1024),
    skin_type_filter text,
    match_threshold  float,
    match_count      int
)
RETURNS TABLE (id uuid, analysis_result jsonb, similarity float)
LANGUAGE sql STABLE AS $$
    SELECT id, analysis_result,
           1 - (embedding <=> query_embedding) AS similarity
    FROM   product_analyses
    WHERE  skin_type = skin_type_filter
      AND  embedding IS NOT NULL
      AND  1 - (embedding <=> query_embedding) > match_threshold
    ORDER BY embedding <=> query_embedding
    LIMIT  match_count;
$$;
─────────────────────────────────────────────────────────────────
"""

import hashlib
import json
import logging
import os
from typing import Optional

import boto3

logger = logging.getLogger(__name__)

TITAN_EMBED_MODEL = "amazon.titan-embed-text-v2:0"
CACHE_SIMILARITY_THRESHOLD = 0.92   # cosine similarity ≥ 0.92 = cache hit


# ── Supabase ────────────────────────────────────────────────────────────────

def _get_supabase():
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


# ── Embeddings ──────────────────────────────────────────────────────────────

def generate_embedding(text: str) -> Optional[list]:
    """
    Generate a 1024-dim vector using Amazon Titan Embed Text v2.
    Returns None on any failure so callers can fall back gracefully.
    """
    try:
        client = boto3.client(
            "bedrock-runtime",
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
        body = json.dumps({
            "inputText": text[:8000],
            "dimensions": 1024,
            "normalize": True,
        })
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


# ── Cache key (fallback when embedding unavailable) ─────────────────────────

def _hash_key(product_name: str, skin_type: str) -> str:
    normalized = f"{product_name.strip().lower()}::{skin_type.strip().lower()}"
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


# ── Cache read ──────────────────────────────────────────────────────────────

def check_cache(
    product_name: str,
    skin_type: str,
    embedding: Optional[list] = None,
) -> Optional[dict]:
    """
    Check Supabase for a cached analysis.

    Priority:
    1. Vector similarity via match_product_analyses RPC (if embedding available)
    2. Exact hash key fallback
    """
    db = _get_supabase()
    if not db:
        return None

    # ── 1. Vector similarity lookup ────────────────────────────────────────
    if embedding:
        try:
            result = db.rpc(
                "match_product_analyses",
                {
                    "query_embedding": embedding,
                    "skin_type_filter": skin_type,
                    "match_threshold": CACHE_SIMILARITY_THRESHOLD,
                    "match_count": 1,
                },
            ).execute()

            if result.data:
                logger.info(
                    f"Vector cache hit: {product_name} / {skin_type} "
                    f"(similarity {result.data[0].get('similarity', '?'):.3f})"
                )
                cached = result.data[0]["analysis_result"]
                if isinstance(cached, str):
                    cached = json.loads(cached)
                cached["cached"] = True
                return cached

        except Exception as e:
            logger.warning(f"Vector cache lookup failed, trying hash fallback: {e}")

    # ── 2. Exact hash fallback ─────────────────────────────────────────────
    try:
        key = _hash_key(product_name, skin_type)
        result = (
            db.table("product_analyses")
            .select("analysis_result")
            .eq("cache_key", key)
            .limit(1)
            .execute()
        )
        if result.data:
            logger.info(f"Hash cache hit: {product_name} / {skin_type}")
            cached = result.data[0]["analysis_result"]
            if isinstance(cached, str):
                cached = json.loads(cached)
            cached["cached"] = True
            return cached

    except Exception as e:
        logger.error(f"Hash cache lookup failed: {e}")

    return None


# ── Cache write ─────────────────────────────────────────────────────────────

def save_to_cache(
    product_name: str,
    skin_type: str,
    analysis: dict,
    embedding: Optional[list] = None,
) -> None:
    """
    Persist analysis + embedding vector to Supabase.
    Skips error responses. Upserts on cache_key.
    """
    db = _get_supabase()
    if not db:
        return

    if analysis.get("error"):
        logger.info("Skipping cache write for error response")
        return

    try:
        key = _hash_key(product_name, skin_type)
        row: dict = {
            "cache_key": key,
            "product_name": product_name,
            "skin_type": skin_type,
            "analysis_result": analysis,
        }
        if embedding:
            row["embedding"] = embedding

        db.table("product_analyses").upsert(
            row, on_conflict="cache_key"
        ).execute()

        logger.info(
            f"Cached: {product_name} / {skin_type}"
            f"{' (with embedding)' if embedding else ' (no embedding)'}"
        )

    except Exception as e:
        logger.error(f"Cache write error: {e}")

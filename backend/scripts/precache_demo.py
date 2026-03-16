"""
Pre-cache demo products for SkinGraph demo day.

Run this script once before the demo to ensure all 3 demo products
load instantly from Supabase cache. No Nova credits spent during live demo.

Usage:
    cd backend
    python scripts/precache_demo.py
"""

import asyncio
import json
import os
import sys

# Add backend root to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

# Import after dotenv so env vars are available
from routes.analyze import analyze_product, AnalyzeRequest


DEMO_PRODUCTS = [
    {
        "product_name": "CeraVe Moisturising Cream",
        "skin_type": "dry",
        "skin_type_inferred": True,
    },
    {
        "product_name": "The Ordinary Niacinamide 10% + Zinc 1%",
        "skin_type": "oily",
        "skin_type_inferred": True,
    },
    {
        "product_name": "La Roche-Posay Cicaplast Baume B5",
        "skin_type": "sensitive",
        "skin_type_inferred": True,
    },
]


async def precache_all():
    print("=" * 60)
    print("SkinGraph — Pre-caching demo products")
    print("=" * 60)

    for i, product in enumerate(DEMO_PRODUCTS, 1):
        name = product["product_name"]
        skin = product["skin_type"]
        print(f"\n[{i}/3] Analyzing: {name} ({skin} skin)...")

        try:
            req = AnalyzeRequest(
                product_name=name,
                skin_type=skin,
                skin_type_inferred=product["skin_type_inferred"],
                images_base64=[],
            )
            result = await analyze_product(req)
            score = result.get("suitability_score", "?")
            n_ingredients = len(result.get("ingredients", []))
            cached = result.get("cached", False)

            if cached:
                print(f"  ⚡ Already cached! Score: {score}/100, {n_ingredients} ingredients")
            else:
                print(f"  ✅ Cached! Score: {score}/100, {n_ingredients} ingredients")
        except Exception as e:
            print(f"  ❌ Failed: {e}")

    print("\n" + "=" * 60)
    print("Done! All demo products are now cached in Supabase.")
    print("They will load instantly on demo day.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(precache_all())

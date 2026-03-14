"""
Open Beauty Facts API — free ingredient lookup, no API key required.
Search URL: https://world.openbeautyfacts.org/cgi/search.pl
"""

import logging
import re
import requests
from typing import Optional

logger = logging.getLogger(__name__)

OBF_SEARCH_URL = "https://world.openbeautyfacts.org/cgi/search.pl"
OBF_TIMEOUT = 10  # seconds


def _clean_ingredients(text: str) -> str:
    """Strip common OBF noise from ingredients text."""
    if not text:
        return ""
    # Remove asterisk annotations and footnotes
    text = re.sub(r"\*+[^,]*", "", text)
    # Remove bracketed numbers like [1], [2]
    text = re.sub(r"\[\d+\]", "", text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Remove trailing punctuation noise
    text = text.rstrip("., ")
    return text


def fetch_ingredients(product_name: str) -> dict:
    """
    Search Open Beauty Facts for a product and return its ingredients.

    Returns:
        {
            "ingredients_text": str | None,
            "product_name": str,
            "brand": str,
            "found": bool,
            "error": str | None,
        }
    """
    base = {
        "ingredients_text": None,
        "product_name": product_name,
        "brand": "",
        "found": False,
        "error": None,
    }

    try:
        params = {
            "search_terms": product_name,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": 8,
            "fields": "product_name,ingredients_text,brands,image_url",
        }

        resp = requests.get(OBF_SEARCH_URL, params=params, timeout=OBF_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        products = data.get("products", [])
        if not products:
            logger.info(f"OBF: no products found for '{product_name}'")
            return base

        # Prefer product that has ingredients_text and a matching name
        def rank(p: dict) -> int:
            score = 0
            if p.get("ingredients_text"):
                score += 10
            pname = (p.get("product_name") or "").lower()
            query = product_name.lower()
            # Boost partial name match
            for word in query.split():
                if word in pname:
                    score += 2
            return score

        best = max(products, key=rank)
        ingredients_text = _clean_ingredients(best.get("ingredients_text", ""))

        return {
            "ingredients_text": ingredients_text or None,
            "product_name": best.get("product_name") or product_name,
            "brand": best.get("brands", ""),
            "found": bool(ingredients_text),
            "error": None,
        }

    except requests.exceptions.Timeout:
        logger.warning(f"OBF timeout for: {product_name}")
        return {**base, "error": "timeout"}
    except requests.exceptions.RequestException as e:
        logger.error(f"OBF request error: {e}")
        return {**base, "error": str(e)}
    except Exception as e:
        logger.error(f"OBF unexpected error: {e}")
        return {**base, "error": str(e)}

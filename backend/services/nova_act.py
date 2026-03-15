"""
Nova Act browser session — brand site claims only (1 session).
Ingredients come from Open Beauty Facts (free API, no scraping needed).
Gracefully returns None if Nova Act SDK is unavailable or times out.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_NOVA_ACT_AVAILABLE: Optional[bool] = None


def _nova_act_available() -> bool:
    global _NOVA_ACT_AVAILABLE
    if _NOVA_ACT_AVAILABLE is None:
        try:
            import nova_act  # noqa: F401
            _NOVA_ACT_AVAILABLE = True
        except ImportError:
            logger.warning("nova_act SDK not installed — Nova Act session disabled")
            _NOVA_ACT_AVAILABLE = False
    return _NOVA_ACT_AVAILABLE


def _get_api_key() -> Optional[str]:
    return os.getenv("NOVA_API_KEY") or os.getenv("NOVA_ACT_API_KEY")


def get_brand_claims(product_name: str) -> Optional[str]:
    """
    Use Nova Act to find official brand marketing claims for the product.
    Navigates to Google, clicks the official brand result, extracts key claims.
    Returns a short summary string, or None on failure / SDK unavailable.
    """
    if not _nova_act_available():
        return None

    api_key = _get_api_key()
    if not api_key:
        logger.warning("No Nova Act API key set — skipping brand claims")
        return None

    try:
        from nova_act import NovaAct

        search_url = (
            "https://www.google.com/search?q="
            + product_name.replace(" ", "+")
            + "+official+site+skin+benefits"
        )

        with NovaAct(api_key=api_key, headless=True) as agent:
            agent.navigate(search_url)
            result = agent.act(
                "Find the official brand marketing claims and key skin benefits "
                "for this skincare product. Summarize in 1-2 sentences. "
                "Return only the claims text — no URLs, no source names."
            )
            claims = getattr(result, "response", str(result)).strip()
            return claims if claims else None

    except Exception as e:
        logger.error(f"Nova Act brand claims error: {e}")
        return None

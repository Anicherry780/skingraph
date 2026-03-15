"""
Lambda trigger — runs the Nova Act brand claims session.

Nova Act sessions: 1 (brand site claims only).
Ingredients come from Open Beauty Facts API — no Nova Act session needed for that.

Priority:
1. AWS Lambda (if LAMBDA_CLAIMS_FN env var set)
2. Direct call fallback (runs get_brand_claims in-process)
"""

import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Optional

import boto3

from services.nova_act import get_brand_claims

logger = logging.getLogger(__name__)

_SESSION_TIMEOUT = 30  # seconds


def _invoke_lambda(function_name: str, payload: dict) -> Optional[dict]:
    """Invoke an AWS Lambda function synchronously."""
    try:
        client = boto3.client(
            "lambda",
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
        response = client.invoke(
            FunctionName=function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload).encode(),
        )
        raw = response["Payload"].read()
        return json.loads(raw)
    except Exception as e:
        logger.error(f"Lambda invoke error ({function_name}): {e}")
        return None


def run_nova_act_parallel(product_name: str) -> dict:
    """
    Run the brand claims Nova Act session.
    Uses Lambda if LAMBDA_CLAIMS_FN is set, otherwise calls directly.

    Returns: {"brand_claims": str | None}
    """
    lambda_claims = os.getenv("LAMBDA_CLAIMS_FN")
    brand_claims: Optional[str] = None

    if lambda_claims:
        logger.info(f"Invoking Lambda for brand claims: {lambda_claims}")
        try:
            result = _invoke_lambda(lambda_claims, {"product_name": product_name})
            brand_claims = result.get("claims") if result else None
        except Exception as e:
            logger.warning(f"Lambda claims failed: {e}")

    else:
        logger.info("Running brand claims Nova Act session directly")
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(get_brand_claims, product_name)
            try:
                brand_claims = future.result(timeout=_SESSION_TIMEOUT)
            except (TimeoutError, Exception) as e:
                logger.warning(f"Brand claims session failed: {e}")

    return {"brand_claims": brand_claims}

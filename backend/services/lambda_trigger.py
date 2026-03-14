"""
Lambda trigger — runs both Nova Act sessions in parallel.

Priority order:
1. AWS Lambda (if LAMBDA_AMAZON_FN + LAMBDA_CLAIMS_FN env vars set)
2. Direct threading fallback (runs nova_act.py functions in threads)

Either way, both sessions run concurrently and results are merged.
"""

import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from typing import Optional

import boto3

from services.nova_act import get_amazon_price, get_brand_claims

logger = logging.getLogger(__name__)

_SESSION_TIMEOUT = 30  # seconds per Nova Act session


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
    Run Amazon price + brand claims lookups in parallel.
    Returns: {"amazon_price": str | None, "brand_claims": str | None}
    """
    lambda_amazon = os.getenv("LAMBDA_AMAZON_FN")
    lambda_claims = os.getenv("LAMBDA_CLAIMS_FN")

    amazon_price: Optional[str] = None
    brand_claims: Optional[str] = None

    if lambda_amazon and lambda_claims:
        # True parallel via Lambda
        logger.info("Using AWS Lambda for parallel Nova Act sessions")
        with ThreadPoolExecutor(max_workers=2) as executor:
            fut_price = executor.submit(
                _invoke_lambda, lambda_amazon, {"product_name": product_name}
            )
            fut_claims = executor.submit(
                _invoke_lambda, lambda_claims, {"product_name": product_name}
            )
            try:
                price_result = fut_price.result(timeout=_SESSION_TIMEOUT)
                amazon_price = price_result.get("price") if price_result else None
            except (TimeoutError, Exception) as e:
                logger.warning(f"Lambda price lookup failed: {e}")

            try:
                claims_result = fut_claims.result(timeout=_SESSION_TIMEOUT)
                brand_claims = claims_result.get("claims") if claims_result else None
            except (TimeoutError, Exception) as e:
                logger.warning(f"Lambda claims lookup failed: {e}")

    else:
        # Threaded fallback — direct nova_act calls
        logger.info("Using threaded fallback for Nova Act sessions")
        with ThreadPoolExecutor(max_workers=2) as executor:
            fut_price = executor.submit(get_amazon_price, product_name)
            fut_claims = executor.submit(get_brand_claims, product_name)

            try:
                amazon_price = fut_price.result(timeout=_SESSION_TIMEOUT)
            except (TimeoutError, Exception) as e:
                logger.warning(f"Amazon price lookup failed: {e}")

            try:
                brand_claims = fut_claims.result(timeout=_SESSION_TIMEOUT)
            except (TimeoutError, Exception) as e:
                logger.warning(f"Brand claims lookup failed: {e}")

    return {
        "amazon_price": amazon_price,
        "brand_claims": brand_claims,
    }

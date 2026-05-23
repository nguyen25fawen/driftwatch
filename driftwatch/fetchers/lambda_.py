"""Fetcher for AWS Lambda function configurations."""

from __future__ import annotations

import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError

from driftwatch.poller import register_fetcher

logger = logging.getLogger(__name__)


def _get_lambda_client(region: str) -> Any:
    return boto3.client("lambda", region_name=region)


@register_fetcher("lambda")
def fetch_lambda_function(resource_id: str, region: str = "us-east-1") -> dict[str, Any]:
    """Fetch configuration for a Lambda function.

    Args:
        resource_id: The Lambda function name or ARN.
        region: AWS region where the function resides.

    Returns:
        A flat dict of relevant configuration fields.

    Raises:
        ClientError: If the AWS API call fails.
    """
    client = _get_lambda_client(region)

    try:
        resp = client.get_function_configuration(FunctionName=resource_id)
    except ClientError as exc:
        logger.error(
            "Failed to fetch Lambda function %s in %s: %s",
            resource_id,
            region,
            exc,
        )
        raise

    # Normalise environment variables — absent key treated as empty dict
    env_vars = resp.get("Environment", {}).get("Variables", {})

    # Layers: extract ARNs only for stable comparison
    layers = sorted(
        layer["Arn"] for layer in resp.get("Layers", [])
    )

    return {
        "function_name": resp["FunctionName"],
        "runtime": resp.get("Runtime", ""),
        "handler": resp.get("Handler", ""),
        "timeout": resp.get("Timeout"),
        "memory_size": resp.get("MemorySize"),
        "role": resp.get("Role", ""),
        "description": resp.get("Description", ""),
        "tracing_mode": resp.get("TracingConfig", {}).get("Mode", "PassThrough"),
        "environment_variables": env_vars,
        "layers": layers,
        "package_type": resp.get("PackageType", "Zip"),
        "architectures": sorted(resp.get("Architectures", ["x86_64"])),
    }

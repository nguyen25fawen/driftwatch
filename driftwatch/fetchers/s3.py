"""AWS S3 bucket config fetcher for DriftWatch."""

from __future__ import annotations

import logging
from typing import Any, Dict

import boto3
from botocore.exceptions import ClientError

from driftwatch.poller import register_fetcher

logger = logging.getLogger(__name__)


def _get_s3_client():
    """Return a boto3 S3 client (thin wrapper to allow mocking in tests)."""
    return boto3.client("s3")


@register_fetcher("s3_bucket")
def fetch_s3_bucket(resource_id: str) -> Dict[str, Any]:
    """Return a normalised config dict for an S3 bucket.

    Collected attributes:
    - versioning_enabled (bool)
    - public_access_block (dict)
    - server_side_encryption (str | None)

    Args:
        resource_id: S3 bucket name.

    Returns:
        Dict of config keys and their current values.

    Raises:
        RuntimeError: If the bucket cannot be accessed.
    """
    client = _get_s3_client()
    config: Dict[str, Any] = {}

    # --- Versioning ---
    try:
        resp = client.get_bucket_versioning(Bucket=resource_id)
        config["versioning_enabled"] = resp.get("Status") == "Enabled"
    except ClientError as exc:
        raise RuntimeError(f"Failed to get versioning for {resource_id}: {exc}") from exc

    # --- Public access block ---
    try:
        resp = client.get_public_access_block(Bucket=resource_id)
        config["public_access_block"] = resp.get("PublicAccessBlockConfiguration", {})
    except ClientError:
        # Bucket may not have the setting configured
        config["public_access_block"] = {}

    # --- Server-side encryption ---
    try:
        resp = client.get_bucket_encryption(Bucket=resource_id)
        rules = (
            resp.get("ServerSideEncryptionConfiguration", {})
            .get("Rules", [{}])[0]
            .get("ApplyServerSideEncryptionByDefault", {})
        )
        config["server_side_encryption"] = rules.get("SSEAlgorithm")
    except ClientError:
        config["server_side_encryption"] = None

    logger.debug("Fetched S3 config for bucket=%s: %s", resource_id, config)
    return config

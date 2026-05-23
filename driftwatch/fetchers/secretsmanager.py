"""Fetcher for AWS Secrets Manager secrets."""
from __future__ import annotations

import boto3
from typing import Any

from driftwatch.poller import register_fetcher, PollResult


def _get_secretsmanager_client(region: str | None = None):
    kwargs = {"region_name": region} if region else {}
    return boto3.client("secretsmanager", **kwargs)


@register_fetcher("secretsmanager_secret")
def fetch_secretsmanager_secret(
    resource_id: str,
    region: str | None = None,
    **_: Any,
) -> PollResult:
    """Fetch metadata for a Secrets Manager secret by name or ARN."""
    client = _get_secretsmanager_client(region)

    try:
        resp = client.describe_secret(SecretId=resource_id)
    except client.exceptions.ResourceNotFoundException:
        return PollResult.ok(
            resource_id=resource_id,
            resource_type="secretsmanager_secret",
            config={},
        )

    rotation_rules = resp.get("RotationRules") or {}
    tags: dict[str, str] = {
        t["Key"]: t["Value"] for t in (resp.get("Tags") or [])
    }

    config: dict[str, Any] = {
        "name": resp.get("Name"),
        "description": resp.get("Description", ""),
        "kms_key_id": resp.get("KmsKeyId", ""),
        "rotation_enabled": resp.get("RotationEnabled", False),
        "rotation_lambda_arn": resp.get("RotationLambdaARN", ""),
        "automatically_after_days": rotation_rules.get(
            "AutomaticallyAfterDays", 0
        ),
        "tags": tags,
    }

    return PollResult.ok(
        resource_id=resource_id,
        resource_type="secretsmanager_secret",
        config=config,
    )

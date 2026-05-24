"""Fetcher for AWS EKS cluster configuration."""
from __future__ import annotations

import boto3
from typing import Any

from driftwatch.poller import register_fetcher, PollResult


def _get_eks_client(region: str | None = None):
    kwargs = {"region_name": region} if region else {}
    return boto3.client("eks", **kwargs)


@register_fetcher("eks_cluster")
def fetch_eks_cluster(resource_id: str, region: str | None = None) -> PollResult:
    """Fetch EKS cluster configuration.

    Args:
        resource_id: The name of the EKS cluster.
        region: AWS region override.

    Returns:
        PollResult with the cluster config or an error.
    """
    client = _get_eks_client(region)

    try:
        resp = client.describe_cluster(name=resource_id)
    except client.exceptions.ResourceNotFoundException:
        return PollResult.ok(resource_id=resource_id, config={})
    except Exception as exc:  # pragma: no cover
        return PollResult(
            resource_id=resource_id,
            resource_type="eks_cluster",
            config={},
            success=False,
            error=str(exc),
        )

    cluster: dict[str, Any] = resp["cluster"]

    logging_types: list[str] = []
    for log_setup in cluster.get("logging", {}).get("clusterLogging", []):
        if log_setup.get("enabled"):
            logging_types.extend(log_setup.get("types", []))

    config = {
        "name": cluster.get("name"),
        "version": cluster.get("version"),
        "role_arn": cluster.get("roleArn"),
        "endpoint_public_access": cluster.get("resourcesVpcConfig", {}).get(
            "endpointPublicAccess", True
        ),
        "endpoint_private_access": cluster.get("resourcesVpcConfig", {}).get(
            "endpointPrivateAccess", False
        ),
        "logging_types": sorted(logging_types),
        "encryption_enabled": len(cluster.get("encryptionConfig", [])) > 0,
        "status": cluster.get("status"),
    }

    return PollResult.ok(resource_id=resource_id, config=config)

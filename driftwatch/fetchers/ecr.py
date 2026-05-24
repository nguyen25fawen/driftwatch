"""Fetcher for Amazon ECR (Elastic Container Registry) repositories."""
from __future__ import annotations

import boto3
from typing import Any

from driftwatch.poller import register_fetcher, PollResult


def _get_ecr_client(region: str | None = None):
    kwargs = {"region_name": region} if region else {}
    return boto3.client("ecr", **kwargs)


@register_fetcher("ecr_repository")
def fetch_ecr_repository(resource_id: str, region: str | None = None) -> PollResult:
    """Fetch configuration for an ECR repository.

    Args:
        resource_id: The ECR repository name.
        region: Optional AWS region override.

    Returns:
        PollResult with repository configuration or error info.
    """
    client = _get_ecr_client(region)

    try:
        resp = client.describe_repositories(repositoryNames=[resource_id])
    except client.exceptions.RepositoryNotFoundException:
        return PollResult.ok(resource_id=resource_id, resource_type="ecr_repository", config={})

    repos = resp.get("repositories", [])
    if not repos:
        return PollResult.ok(resource_id=resource_id, resource_type="ecr_repository", config={})

    repo = repos[0]

    # Fetch image scanning configuration
    scan_config = repo.get("imageScanningConfiguration", {})

    # Fetch lifecycle policy (may not exist)
    lifecycle_policy_text: str | None = None
    try:
        lp_resp = client.get_lifecycle_policy(repositoryName=resource_id)
        lifecycle_policy_text = lp_resp.get("lifecyclePolicyText")
    except client.exceptions.LifecyclePolicyNotFoundException:
        lifecycle_policy_text = None

    config: dict[str, Any] = {
        "repository_name": repo.get("repositoryName"),
        "image_tag_mutability": repo.get("imageTagMutability", "MUTABLE"),
        "scan_on_push": scan_config.get("scanOnPush", False),
        "encryption_type": repo.get("encryptionConfiguration", {}).get("encryptionType", "AES256"),
        "lifecycle_policy_defined": lifecycle_policy_text is not None,
    }

    return PollResult.ok(resource_id=resource_id, resource_type="ecr_repository", config=config)

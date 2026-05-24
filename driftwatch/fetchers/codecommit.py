"""Fetcher for AWS CodeCommit repository configuration."""

from __future__ import annotations

import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError

from driftwatch.poller import register_fetcher

logger = logging.getLogger(__name__)


def _get_codecommit_client(region: str | None = None) -> Any:
    kwargs = {"region_name": region} if region else {}
    return boto3.client("codecommit", **kwargs)


@register_fetcher("codecommit_repository")
def fetch_codecommit_repository(resource_id: str, region: str | None = None) -> dict[str, Any]:
    """Fetch configuration for a CodeCommit repository.

    Args:
        resource_id: The name of the CodeCommit repository.
        region: AWS region override.

    Returns:
        A dict of repository configuration fields, or empty dict on error.
    """
    client = _get_codecommit_client(region)
    try:
        resp = client.get_repository(repositoryName=resource_id)
        meta = resp["repositoryMetadata"]
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code in ("RepositoryDoesNotExistException", "NoSuchEntityException"):
            logger.warning("CodeCommit repository %r not found.", resource_id)
        else:
            logger.error("Error fetching CodeCommit repository %r: %s", resource_id, exc)
        return {}

    config: dict[str, Any] = {
        "repository_name": meta.get("repositoryName", ""),
        "default_branch": meta.get("defaultBranch", ""),
        "repository_description": meta.get("repositoryDescription", ""),
    }

    # Fetch approval rule templates associated with this repository
    try:
        rules_resp = client.list_associated_approval_rule_templates_for_repository(
            repositoryName=resource_id
        )
        config["approval_rule_templates"] = sorted(
            rules_resp.get("approvalRuleTemplateNames", [])
        )
    except ClientError as exc:
        logger.warning(
            "Could not fetch approval rule templates for %r: %s", resource_id, exc
        )
        config["approval_rule_templates"] = []

    return config

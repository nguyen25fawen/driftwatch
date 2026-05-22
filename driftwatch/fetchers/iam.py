"""IAM role/policy fetcher for DriftWatch.

Polls AWS IAM roles and returns a normalized config dict
suitable for drift detection against a stored baseline.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from driftwatch.poller import PollResult, register_fetcher

logger = logging.getLogger(__name__)


def _get_iam_client(region: str) -> Any:
    """Return a boto3 IAM client.  IAM is global, but region is accepted
    for interface consistency with other fetchers."""
    return boto3.client("iam", region_name=region)


@register_fetcher("iam_role")
def fetch_iam_role(resource_id: str, region: str, **kwargs: Any) -> PollResult:
    """Fetch key attributes of an IAM role.

    Parameters
    ----------
    resource_id:
        The IAM role name (not ARN).
    region:
        AWS region string (used only for client construction; IAM is global).

    Returns
    -------
    PollResult
        ``ok=True`` with a config dict on success, or ``ok=False`` with an
        error message when the role cannot be retrieved.
    """
    client = _get_iam_client(region)

    # ── Fetch the role itself ────────────────────────────────────────────────
    try:
        role_resp = client.get_role(RoleName=resource_id)
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code == "NoSuchEntity":
            return PollResult.fail(f"IAM role '{resource_id}' not found")
        logger.exception("ClientError fetching IAM role '%s'", resource_id)
        return PollResult.fail(str(exc))
    except BotoCoreError as exc:
        logger.exception("BotoCoreError fetching IAM role '%s'", resource_id)
        return PollResult.fail(str(exc))

    role = role_resp["Role"]

    # ── Fetch attached managed policies ──────────────────────────────────────
    try:
        paginator = client.get_paginator("list_attached_role_policies")
        attached: list[str] = []
        for page in paginator.paginate(RoleName=resource_id):
            for policy in page["AttachedPolicies"]:
                attached.append(policy["PolicyArn"])
    except (ClientError, BotoCoreError) as exc:
        logger.warning(
            "Could not list attached policies for role '%s': %s",
            resource_id,
            exc,
        )
        attached = []

    # ── Fetch inline policy names ────────────────────────────────────────────
    try:
        inline_resp = client.list_role_policies(RoleName=resource_id)
        inline_policies: list[str] = inline_resp.get("PolicyNames", [])
    except (ClientError, BotoCoreError) as exc:
        logger.warning(
            "Could not list inline policies for role '%s': %s",
            resource_id,
            exc,
        )
        inline_policies = []

    # ── Normalise the assume-role policy document ────────────────────────────
    raw_doc = role.get("AssumeRolePolicyDocument", {})
    # boto3 already URL-decodes the document; normalise to a stable string
    # so it can be compared as a JSON-serialised value in the baseline.
    assume_role_policy = json.dumps(raw_doc, sort_keys=True)

    config: dict[str, Any] = {
        "role_name": role["RoleName"],
        "role_id": role["RoleId"],
        "arn": role["Arn"],
        "path": role.get("Path", "/"),
        "max_session_duration": role.get("MaxSessionDuration", 3600),
        "assume_role_policy": assume_role_policy,
        "attached_policies": sorted(attached),
        "inline_policies": sorted(inline_policies),
        "description": role.get("Description", ""),
        "permissions_boundary": (
            role["PermissionsBoundary"]["PermissionsBoundaryArn"]
            if "PermissionsBoundary" in role
            else None
        ),
    }

    logger.debug("Fetched IAM role '%s': %s", resource_id, config)
    return PollResult.ok(config)

"""IAM role fetcher for DriftWatch."""
from __future__ import annotations

import json
import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError

from driftwatch.poller import register_fetcher

logger = logging.getLogger(__name__)


def _get_iam_client(region: str):
    return boto3.client("iam", region_name=region)


@register_fetcher("iam_role")
def fetch_iam_role(resource_id: str, region: str) -> dict[str, Any]:
    """Fetch IAM role config and inline/attached policy names."""
    client = _get_iam_client(region)

    try:
        role_resp = client.get_role(RoleName=resource_id)
    except ClientError as exc:
        logger.error("Failed to get IAM role %s: %s", resource_id, exc)
        raise

    role = role_resp["Role"]

    # Attached managed policies
    attached_resp = client.list_attached_role_policies(RoleName=resource_id)
    attached = sorted(
        p["PolicyName"] for p in attached_resp.get("AttachedPolicies", [])
    )

    # Inline policy names
    inline_resp = client.list_role_policies(RoleName=resource_id)
    inline = sorted(inline_resp.get("PolicyNames", []))

    assume_doc = role.get("AssumeRolePolicyDocument", {})
    if isinstance(assume_doc, str):
        assume_doc = json.loads(assume_doc)

    return {
        "role_name": role["RoleName"],
        "path": role.get("Path", "/"),
        "max_session_duration": role.get("MaxSessionDuration", 3600),
        "assume_role_policy_statement_count": len(
            assume_doc.get("Statement", [])
        ),
        "attached_policies": attached,
        "inline_policies": inline,
        "tags": {
            t["Key"]: t["Value"] for t in role.get("Tags", [])
        },
    }

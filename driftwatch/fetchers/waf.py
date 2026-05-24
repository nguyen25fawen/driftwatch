"""Fetcher for AWS WAFv2 Web ACLs."""
from __future__ import annotations

import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError

from driftwatch.poller import register_fetcher

logger = logging.getLogger(__name__)


def _get_waf_client(region: str | None = None) -> Any:
    kwargs = {"region_name": region} if region else {}
    return boto3.client("wafv2", **kwargs)


@register_fetcher("waf_web_acl")
def fetch_waf_web_acl(resource_id: str, region: str | None = None) -> dict[str, Any]:
    """Fetch WAFv2 Web ACL configuration.

    Args:
        resource_id: The Web ACL ID (format: ``<name>/<id>``).
        region: AWS region; uses the default if omitted.

    Returns:
        Normalised config dict, or empty dict if the resource is not found.
    """
    client = _get_waf_client(region)

    # resource_id may be "<name>/<id>" or just the ARN-style id
    parts = resource_id.split("/", 1)
    name = parts[0]
    wacl_id = parts[1] if len(parts) == 2 else parts[0]

    try:
        resp = client.get_web_acl(Name=name, Scope="REGIONAL", Id=wacl_id)
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code in ("WAFNonexistentItemException", "WAFInvalidParameterException"):
            logger.warning("WAF Web ACL not found: %s", resource_id)
            return {}
        raise

    acl = resp["WebACL"]
    default_action = list(acl.get("DefaultAction", {}).keys())
    default_action_str = default_action[0].lower() if default_action else "unknown"

    rules = sorted(
        [
            {
                "name": r["Name"],
                "priority": r["Priority"],
                "action": list(r.get("Action", r.get("OverrideAction", {}))).pop().lower()
                if r.get("Action") or r.get("OverrideAction")
                else "managed",
            }
            for r in acl.get("Rules", [])
        ],
        key=lambda x: x["priority"],
    )

    return {
        "name": acl["Name"],
        "id": acl["Id"],
        "default_action": default_action_str,
        "managed_by_firewall_manager": acl.get("ManagedByFirewallManager", False),
        "rule_count": len(rules),
        "rules": rules,
        "capacity": acl.get("Capacity", 0),
    }

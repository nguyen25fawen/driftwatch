"""Fetcher for AWS VPC configuration."""

from __future__ import annotations

import boto3
from typing import Any

from driftwatch.poller import register_fetcher, PollResult


def _get_vpc_client(region: str | None = None):
    kwargs = {"region_name": region} if region else {}
    return boto3.client("ec2", **kwargs)


@register_fetcher("vpc")
def fetch_vpc(resource_id: str, region: str | None = None) -> PollResult:
    """Fetch configuration for a VPC by its ID."""
    client = _get_vpc_client(region)

    resp = client.describe_vpcs(VpcIds=[resource_id])
    vpcs = resp.get("Vpcs", [])
    if not vpcs:
        return PollResult.ok(resource_id=resource_id, config={})

    vpc: dict[str, Any] = vpcs[0]

    # Fetch DHCP options for additional config detail
    dhcp_options_id = vpc.get("DhcpOptionsId", "")

    # Fetch flow logs enabled status
    flow_logs_resp = client.describe_flow_logs(
        Filters=[{"Name": "resource-id", "Values": [resource_id]}]
    )
    flow_logs_enabled = len(flow_logs_resp.get("FlowLogs", [])) > 0

    # Collect tag keys (sorted for determinism)
    tags = {t["Key"]: t["Value"] for t in vpc.get("Tags", [])}

    config: dict[str, Any] = {
        "cidr_block": vpc.get("CidrBlock", ""),
        "state": vpc.get("State", ""),
        "is_default": vpc.get("IsDefault", False),
        "dhcp_options_id": dhcp_options_id,
        "instance_tenancy": vpc.get("InstanceTenancy", "default"),
        "flow_logs_enabled": flow_logs_enabled,
        "ipv6_cidr_blocks": sorted(
            [a.get("Ipv6CidrBlock", "") for a in vpc.get("Ipv6CidrBlockAssociationSet", [])]
        ),
        "tags": tags,
    }

    return PollResult.ok(resource_id=resource_id, config=config)

"""Fetcher for AWS Route53 hosted zones."""
from __future__ import annotations

import boto3
from typing import Any

from driftwatch.poller import register_fetcher, PollResult


def _get_route53_client(region: str) -> Any:
    return boto3.client("route53", region_name=region)


@register_fetcher("route53_hosted_zone")
def fetch_route53_hosted_zone(resource_id: str, region: str) -> PollResult:
    """Fetch key configuration fields for a Route53 hosted zone.

    Args:
        resource_id: The hosted zone ID (e.g. ``Z1D633PJN98FT9``).
        region:      AWS region (Route53 is global but the client still needs one).

    Returns:
        A :class:`~driftwatch.poller.PollResult` with the zone config dict.
    """
    client = _get_route53_client(region)

    try:
        zone_resp = client.get_hosted_zone(Id=resource_id)
    except client.exceptions.NoSuchHostedZone:
        return PollResult.ok(resource_id=resource_id, resource_type="route53_hosted_zone", config={})

    zone = zone_resp["HostedZone"]
    config_block = zone_resp.get("VPCs", [])

    config: dict[str, Any] = {
        "name": zone["Name"],
        "private_zone": zone["Config"]["PrivateZone"],
        "comment": zone["Config"].get("Comment", ""),
        "record_count": zone["ResourceRecordSetCount"],
        "vpcs": sorted(
            [{"vpc_id": v["VPCId"], "vpc_region": v["VPCRegion"]} for v in config_block],
            key=lambda x: x["vpc_id"],
        ),
    }

    return PollResult.ok(
        resource_id=resource_id,
        resource_type="route53_hosted_zone",
        config=config,
    )

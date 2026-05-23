"""Fetcher for AWS Elastic Load Balancer (ALB/NLB) configuration."""
from __future__ import annotations

import boto3
from typing import Any

from driftwatch.poller import register_fetcher, PollResult


def _get_elb_client(region: str | None = None):
    kwargs = {"region_name": region} if region else {}
    return boto3.client("elbv2", **kwargs)


@register_fetcher("elb")
def fetch_elb(resource_id: str, region: str | None = None) -> PollResult:
    """Fetch key configuration attributes for an ALB/NLB by ARN or name."""
    client = _get_elb_client(region)

    try:
        resp = client.describe_load_balancers(Names=[resource_id])
    except client.exceptions.LoadBalancerNotFoundException:
        return PollResult.ok(resource_id, "elb", {})
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"Failed to describe ELB '{resource_id}': {exc}") from exc

    lbs = resp.get("LoadBalancers", [])
    if not lbs:
        return PollResult.ok(resource_id, "elb", {})

    lb = lbs[0]
    lb_arn = lb["LoadBalancerArn"]

    # Fetch attributes
    attr_resp = client.describe_load_balancer_attributes(LoadBalancerArn=lb_arn)
    attributes: dict[str, Any] = {
        a["Key"]: a["Value"] for a in attr_resp.get("Attributes", [])
    }

    config: dict[str, Any] = {
        "name": lb.get("LoadBalancerName"),
        "type": lb.get("Type"),
        "scheme": lb.get("Scheme"),
        "ip_address_type": lb.get("IpAddressType"),
        "deletion_protection_enabled": attributes.get(
            "deletion_protection.enabled", "false"
        ),
        "access_logs_enabled": attributes.get("access_logs.s3.enabled", "false"),
        "idle_timeout_seconds": attributes.get("idle_timeout.timeout_seconds", "60"),
        "availability_zones": sorted(
            az["ZoneName"] for az in lb.get("AvailabilityZones", [])
        ),
    }

    return PollResult.ok(resource_id, "elb", config)

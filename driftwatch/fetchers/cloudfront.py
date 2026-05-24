"""Fetcher for AWS CloudFront distribution configurations."""
from __future__ import annotations

import boto3
from botocore.exceptions import ClientError

from driftwatch.poller import register_fetcher, PollResult


def _get_cloudfront_client(region: str):
    return boto3.client("cloudfront", region_name=region)


@register_fetcher("cloudfront_distribution")
def fetch_cloudfront_distribution(resource_id: str, region: str) -> PollResult:
    """Fetch key configuration fields for a CloudFront distribution.

    Args:
        resource_id: The CloudFront distribution ID (e.g. ``E1ABCDEF123456``).
        region:      AWS region (CloudFront is global but the client still
                     accepts a region for credential resolution).

    Returns:
        A :class:`PollResult` whose ``config`` dict contains the normalised
        distribution settings used for drift comparison.
    """
    client = _get_cloudfront_client(region)
    try:
        resp = client.get_distribution(Id=resource_id)
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code in ("NoSuchDistribution", "AccessDenied"):
            return PollResult(resource_id=resource_id, resource_type="cloudfront_distribution", config={})
        raise

    dist = resp["Distribution"]["DistributionConfig"]
    origins = sorted(
        [
            {
                "domain_name": o["DomainName"],
                "origin_id": o["Id"],
                "protocol_policy": o.get("CustomOriginConfig", {}).get(
                    "OriginProtocolPolicy", "s3"
                ),
            }
            for o in dist.get("Origins", {}).get("Items", [])
        ],
        key=lambda x: x["origin_id"],
    )

    cache_behaviours = dist.get("DefaultCacheBehavior", {})
    config = {
        "enabled": dist.get("Enabled", False),
        "comment": dist.get("Comment", ""),
        "price_class": dist.get("PriceClass", "PriceClass_All"),
        "http_version": dist.get("HttpVersion", "http2"),
        "ipv6_enabled": dist.get("IsIPV6Enabled", False),
        "default_root_object": dist.get("DefaultRootObject", ""),
        "viewer_protocol_policy": cache_behaviours.get("ViewerProtocolPolicy", ""),
        "compress": cache_behaviours.get("Compress", False),
        "origins": origins,
        "aliases": sorted(dist.get("Aliases", {}).get("Items", [])),
        "web_acl_id": dist.get("WebACLId", ""),
    }
    return PollResult(
        resource_id=resource_id,
        resource_type="cloudfront_distribution",
        config=config,
    )

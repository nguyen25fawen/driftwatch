"""Fetcher for AWS CloudTrail trail configuration."""
from __future__ import annotations

import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError

from driftwatch.poller import register_fetcher

logger = logging.getLogger(__name__)


def _get_cloudtrail_client(region: str | None = None) -> Any:
    kwargs = {"region_name": region} if region else {}
    return boto3.client("cloudtrail", **kwargs)


@register_fetcher("cloudtrail")
def fetch_cloudtrail_trail(resource_id: str, region: str | None = None) -> dict[str, Any]:
    """Return a normalised config dict for a CloudTrail trail.

    Args:
        resource_id: The trail ARN or name.
        region: Optional AWS region override.

    Returns:
        A flat dict of trail attributes, or an empty dict on error.
    """
    client = _get_cloudtrail_client(region)
    try:
        response = client.describe_trails(
            trailNameList=[resource_id],
            includeShadowTrails=False,
        )
    except ClientError as exc:
        logger.warning("CloudTrail describe_trails failed for %s: %s", resource_id, exc)
        return {}

    trails = response.get("trailList", [])
    if not trails:
        logger.warning("No CloudTrail trail found for resource_id=%s", resource_id)
        return {}

    trail = trails[0]

    # Fetch event selectors for logging detail
    try:
        sel_response = client.get_event_selectors(TrailName=resource_id)
        event_selectors = sel_response.get("EventSelectors", [])
    except ClientError as exc:
        logger.warning("get_event_selectors failed for %s: %s", resource_id, exc)
        event_selectors = []

    read_write_types = sorted(
        {es.get("ReadWriteType", "All") for es in event_selectors}
    )

    return {
        "name": trail.get("Name"),
        "s3_bucket_name": trail.get("S3BucketName"),
        "include_global_service_events": trail.get("IncludeGlobalServiceEvents", False),
        "is_multi_region_trail": trail.get("IsMultiRegionTrail", False),
        "log_file_validation_enabled": trail.get("LogFileValidationEnabled", False),
        "kms_key_id": trail.get("KMSKeyId"),
        "cloud_watch_logs_log_group_arn": trail.get("CloudWatchLogsLogGroupArn"),
        "has_custom_event_selectors": trail.get("HasCustomEventSelectors", False),
        "event_selector_read_write_types": read_write_types,
    }

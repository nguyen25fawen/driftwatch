"""Fetcher for AWS Kinesis Data Streams."""

from __future__ import annotations

import boto3
from typing import Any

from driftwatch.poller import register_fetcher, PollResult


def _get_kinesis_client(region: str | None = None) -> Any:
    kwargs = {"region_name": region} if region else {}
    return boto3.client("kinesis", **kwargs)


@register_fetcher("kinesis_stream")
def fetch_kinesis_stream(
    resource_id: str,
    region: str | None = None,
    **_: Any,
) -> PollResult:
    """Fetch configuration for a Kinesis Data Stream.

    Args:
        resource_id: The name of the Kinesis stream.
        region: Optional AWS region override.

    Returns:
        PollResult with stream configuration fields.
    """
    client = _get_kinesis_client(region)

    try:
        response = client.describe_stream_summary(StreamName=resource_id)
    except client.exceptions.ResourceNotFoundException:
        return PollResult.ok(
            resource_id=resource_id,
            resource_type="kinesis_stream",
            config={},
        )

    summary = response["StreamDescriptionSummary"]

    config: dict[str, Any] = {
        "stream_name": summary["StreamName"],
        "stream_status": summary["StreamStatus"],
        "shard_count": summary["OpenShardCount"],
        "retention_period_hours": summary["RetentionPeriodHours"],
        "encryption_type": summary.get("EncryptionType", "NONE"),
        "key_id": summary.get("KeyId", ""),
        "enhanced_monitoring": sorted(
            [m["ShardLevelMetrics"] for m in summary.get("EnhancedMonitoring", [])]
        ),
    }

    return PollResult.ok(
        resource_id=resource_id,
        resource_type="kinesis_stream",
        config=config,
    )

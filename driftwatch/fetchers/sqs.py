"""Fetcher for AWS SQS queue attributes."""

from __future__ import annotations

import boto3
from typing import Any

from driftwatch.poller import register_fetcher, PollResult

_sqs_client = None


def _get_sqs_client() -> Any:
    global _sqs_client
    if _sqs_client is None:
        _sqs_client = boto3.client("sqs")
    return _sqs_client


@register_fetcher("sqs_queue")
def fetch_sqs_queue(resource_id: str, region: str | None = None) -> PollResult:
    """Fetch SQS queue attributes for drift detection.

    Args:
        resource_id: The SQS queue URL.
        region: Optional AWS region override.

    Returns:
        PollResult with queue attributes or error details.
    """
    try:
        client = _get_sqs_client()
        response = client.get_queue_attributes(
            QueueUrl=resource_id,
            AttributeNames=["All"],
        )
        attrs = response.get("Attributes", {})

        config = {
            "visibility_timeout": int(attrs.get("VisibilityTimeout", 0)),
            "max_message_size": int(attrs.get("MaximumMessageSize", 0)),
            "message_retention_seconds": int(attrs.get("MessageRetentionPeriod", 0)),
            "delay_seconds": int(attrs.get("DelaySeconds", 0)),
            "receive_wait_time_seconds": int(attrs.get("ReceiveMessageWaitTimeSeconds", 0)),
            "fifo_queue": attrs.get("FifoQueue", "false").lower() == "true",
            "content_based_deduplication": attrs.get("ContentBasedDeduplication", "false").lower() == "true",
            "kms_master_key_id": attrs.get("KmsMasterKeyId", ""),
            "policy": attrs.get("Policy", ""),
        }
        return PollResult.ok(resource_id=resource_id, resource_type="sqs_queue", config=config)
    except Exception as exc:  # pragma: no cover
        return PollResult.error(resource_id=resource_id, resource_type="sqs_queue", message=str(exc))

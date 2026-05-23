"""Fetcher for AWS SNS topic configuration."""
from __future__ import annotations

import json
import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError

from driftwatch.poller import register_fetcher

logger = logging.getLogger(__name__)


def _get_sns_client(region: str):
    return boto3.client("sns", region_name=region)


@register_fetcher("sns_topic")
def fetch_sns_topic(resource_id: str, region: str = "us-east-1") -> dict[str, Any]:
    """Fetch key configuration fields for an SNS topic by ARN.

    Args:
        resource_id: The ARN of the SNS topic.
        region: AWS region where the topic lives.

    Returns:
        A flat dict of normalised topic attributes.

    Raises:
        ClientError: Propagated from boto3 on unexpected API errors.
    """
    client = _get_sns_client(region)

    try:
        response = client.get_topic_attributes(TopicArn=resource_id)
    except ClientError as exc:
        logger.error("Failed to fetch SNS topic %s: %s", resource_id, exc)
        raise

    attrs = response.get("Attributes", {})

    # Parse the policy document if present so we store a stable structure.
    raw_policy = attrs.get("Policy")
    policy = json.loads(raw_policy) if raw_policy else None

    raw_delivery = attrs.get("EffectiveDeliveryPolicy")
    delivery_policy = json.loads(raw_delivery) if raw_delivery else None

    return {
        "topic_arn": attrs.get("TopicArn", resource_id),
        "display_name": attrs.get("DisplayName", ""),
        "subscriptions_confirmed": int(attrs.get("SubscriptionsConfirmed", 0)),
        "subscriptions_pending": int(attrs.get("SubscriptionsPending", 0)),
        "kms_master_key_id": attrs.get("KmsMasterKeyId", ""),
        "fifo_topic": attrs.get("FifoTopic", "false").lower() == "true",
        "content_based_deduplication": attrs.get(
            "ContentBasedDeduplication", "false"
        ).lower()
        == "true",
        "policy": policy,
        "delivery_policy": delivery_policy,
    }

"""Fetcher for AWS EC2 instance configurations."""

from __future__ import annotations

import logging
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from driftwatch.poller import register_fetcher

logger = logging.getLogger(__name__)


def _get_ec2_client(region: str):
    """Return a boto3 EC2 client for the given region."""
    return boto3.client("ec2", region_name=region)


@register_fetcher("ec2_instance")
def fetch_ec2_instance(resource_id: str, region: str = "us-east-1") -> dict[str, Any]:
    """Fetch the configuration of a single EC2 instance by instance ID.

    Returns a flat dict of relevant attributes suitable for drift comparison.

    Raises:
        ValueError: if the instance is not found.
        RuntimeError: on AWS API errors.
    """
    client = _get_ec2_client(region)

    try:
        response = client.describe_instances(InstanceIds=[resource_id])
    except ClientError as exc:
        error_code = exc.response["Error"]["Code"]
        if error_code == "InvalidInstanceID.NotFound":
            raise ValueError(f"EC2 instance not found: {resource_id}") from exc
        raise RuntimeError(f"AWS ClientError fetching {resource_id}: {exc}") from exc
    except BotoCoreError as exc:
        raise RuntimeError(f"BotoCoreError fetching {resource_id}: {exc}") from exc

    reservations = response.get("Reservations", [])
    if not reservations or not reservations[0].get("Instances"):
        raise ValueError(f"EC2 instance not found: {resource_id}")

    instance = reservations[0]["Instances"][0]

    config: dict[str, Any] = {
        "instance_type": instance.get("InstanceType"),
        "state": instance.get("State", {}).get("Name"),
        "image_id": instance.get("ImageId"),
        "key_name": instance.get("KeyName"),
        "monitoring_enabled": instance.get("Monitoring", {}).get("State") == "enabled",
        "ebs_optimized": instance.get("EbsOptimized", False),
        "vpc_id": instance.get("VpcId"),
        "subnet_id": instance.get("SubnetId"),
        "security_group_ids": sorted(
            sg["GroupId"] for sg in instance.get("SecurityGroups", [])
        ),
        "iam_instance_profile": (
            instance.get("IamInstanceProfile", {}).get("Arn")
        ),
        "tags": {
            tag["Key"]: tag["Value"]
            for tag in instance.get("Tags", [])
        },
    }

    logger.debug("Fetched EC2 instance config for %s: %s", resource_id, config)
    return config

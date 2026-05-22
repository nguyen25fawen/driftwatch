"""Fetcher for AWS RDS DB instance configurations."""

from __future__ import annotations

import logging
from typing import Any, Dict

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from driftwatch.poller import register_fetcher

logger = logging.getLogger(__name__)


def _get_rds_client(region: str):
    """Return a boto3 RDS client for *region*."""
    return boto3.client("rds", region_name=region)


@register_fetcher("rds_instance")
def fetch_rds_instance(resource_id: str, region: str = "us-east-1") -> Dict[str, Any]:
    """Fetch configuration fields for an RDS DB instance.

    Args:
        resource_id: The DB instance identifier.
        region: AWS region where the instance lives.

    Returns:
        A dict containing selected configuration fields.

    Raises:
        ValueError: If the instance cannot be found or the API call fails.
    """
    client = _get_rds_client(region)

    try:
        response = client.describe_db_instances(DBInstanceIdentifier=resource_id)
    except (BotoCoreError, ClientError) as exc:
        raise ValueError(
            f"Failed to describe RDS instance '{resource_id}': {exc}"
        ) from exc

    instances = response.get("DBInstances", [])
    if not instances:
        raise ValueError(f"RDS instance '{resource_id}' not found in region '{region}'")

    inst = instances[0]

    return {
        "db_instance_identifier": inst.get("DBInstanceIdentifier"),
        "db_instance_class": inst.get("DBInstanceClass"),
        "engine": inst.get("Engine"),
        "engine_version": inst.get("EngineVersion"),
        "multi_az": inst.get("MultiAZ"),
        "publicly_accessible": inst.get("PubliclyAccessible"),
        "storage_encrypted": inst.get("StorageEncrypted"),
        "deletion_protection": inst.get("DeletionProtection"),
        "backup_retention_period": inst.get("BackupRetentionPeriod"),
        "db_subnet_group": (
            inst.get("DBSubnetGroup", {}).get("DBSubnetGroupName")
        ),
    }

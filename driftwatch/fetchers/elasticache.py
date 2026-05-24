"""Fetcher for AWS ElastiCache replication groups."""
from __future__ import annotations

import boto3
from typing import Any

from driftwatch.poller import register_fetcher, PollResult


def _get_elasticache_client(region: str | None = None):
    kwargs = {"region_name": region} if region else {}
    return boto3.client("elasticache", **kwargs)


@register_fetcher("elasticache_replication_group")
def fetch_elasticache_replication_group(
    resource_id: str,
    region: str | None = None,
    **_: Any,
) -> PollResult:
    """Fetch config for an ElastiCache replication group."""
    client = _get_elasticache_client(region)

    resp = client.describe_replication_groups(
        ReplicationGroupId=resource_id
    )
    groups = resp.get("ReplicationGroups", [])
    if not groups:
        return PollResult.ok(resource_id, "elasticache_replication_group", {})

    group = groups[0]

    # Collect member cluster node types (all should be the same)
    node_groups = group.get("NodeGroups", [])
    num_node_groups = len(node_groups)
    num_replicas = max(
        (len(ng.get("NodeGroupMembers", [])) - 1 for ng in node_groups),
        default=0,
    )

    config: dict[str, Any] = {
        "description": group.get("Description", ""),
        "status": group.get("Status", ""),
        "multi_az": group.get("MultiAZ", "disabled"),
        "automatic_failover": group.get("AutomaticFailover", "disabled"),
        "at_rest_encryption": group.get("AtRestEncryptionEnabled", False),
        "transit_encryption": group.get("TransitEncryptionEnabled", False),
        "num_node_groups": num_node_groups,
        "num_replicas_per_node_group": num_replicas,
        "snapshotting_cluster_id": group.get("SnapshottingClusterId", ""),
        "snapshot_retention_limit": group.get("SnapshotRetentionLimit", 0),
        "snapshot_window": group.get("SnapshotWindow", ""),
        "cache_node_type": group.get("CacheNodeType", ""),
        "auth_token_enabled": group.get("AuthTokenEnabled", False),
        "cluster_mode": group.get("ClusterMode", "disabled"),
    }

    return PollResult.ok(resource_id, "elasticache_replication_group", config)

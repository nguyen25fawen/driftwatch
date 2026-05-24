"""Fetcher for AWS OpenSearch (Elasticsearch) domain configurations."""
from __future__ import annotations

import boto3
from typing import Any

from driftwatch.poller import register_fetcher, PollResult


def _get_opensearch_client(region: str | None = None) -> Any:
    kwargs = {"region_name": region} if region else {}
    return boto3.client("opensearch", **kwargs)


@register_fetcher("opensearch_domain")
def fetch_opensearch_domain(resource_id: str, region: str | None = None) -> PollResult:
    """Fetch configuration for an OpenSearch domain.

    Args:
        resource_id: The domain name.
        region: Optional AWS region override.

    Returns:
        PollResult with the domain config or an error.
    """
    client = _get_opensearch_client(region)

    try:
        response = client.describe_domain(DomainName=resource_id)
    except client.exceptions.ResourceNotFoundException:
        return PollResult.ok(resource_id, "opensearch_domain", {})
    except Exception as exc:  # pragma: no cover
        return PollResult(
            resource_id=resource_id,
            resource_type="opensearch_domain",
            config={},
            success=False,
            error=str(exc),
        )

    status = response.get("DomainStatus", {})

    engine_version = status.get("EngineVersion", "")
    cluster_cfg = status.get("ClusterConfig", {})
    ebs_options = status.get("EBSOptions", {})
    encrypt_at_rest = status.get("EncryptionAtRestOptions", {})
    node_to_node = status.get("NodeToNodeEncryptionOptions", {})
    advanced = status.get("AdvancedOptions", {})

    config: dict[str, Any] = {
        "engine_version": engine_version,
        "instance_type": cluster_cfg.get("InstanceType", ""),
        "instance_count": cluster_cfg.get("InstanceCount", 1),
        "dedicated_master_enabled": cluster_cfg.get("DedicatedMasterEnabled", False),
        "zone_awareness_enabled": cluster_cfg.get("ZoneAwarenessEnabled", False),
        "ebs_enabled": ebs_options.get("EBSEnabled", False),
        "volume_type": ebs_options.get("VolumeType", ""),
        "volume_size": ebs_options.get("VolumeSize", 0),
        "encrypt_at_rest": encrypt_at_rest.get("Enabled", False),
        "node_to_node_encryption": node_to_node.get("Enabled", False),
        "rest_action_multi_allow_explicit_index": advanced.get(
            "rest.action.multi.allow_explicit_index", "true"
        ),
    }

    return PollResult.ok(resource_id, "opensearch_domain", config)

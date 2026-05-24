"""Tests for the ElastiCache replication group fetcher."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.poller import _FETCHER_REGISTRY
from driftwatch.fetchers.elasticache import fetch_elasticache_replication_group


RG_ID = "my-redis-cluster"


def _make_replication_group(**overrides) -> dict:
    base = {
        "ReplicationGroupId": RG_ID,
        "Description": "Test cluster",
        "Status": "available",
        "MultiAZ": "enabled",
        "AutomaticFailover": "enabled",
        "AtRestEncryptionEnabled": True,
        "TransitEncryptionEnabled": True,
        "SnapshotRetentionLimit": 7,
        "SnapshotWindow": "03:00-04:00",
        "CacheNodeType": "cache.r6g.large",
        "AuthTokenEnabled": True,
        "ClusterMode": "disabled",
        "NodeGroups": [
            {
                "NodeGroupId": "0001",
                "NodeGroupMembers": [
                    {"CacheClusterId": "my-redis-cluster-0001-001"},
                    {"CacheClusterId": "my-redis-cluster-0001-002"},
                    {"CacheClusterId": "my-redis-cluster-0001-003"},
                ],
            }
        ],
    }
    base.update(overrides)
    return base


@pytest.fixture()
def mock_ec_client():
    with patch(
        "driftwatch.fetchers.elasticache._get_elasticache_client"
    ) as mock_factory:
        client = MagicMock()
        mock_factory.return_value = client
        yield client


def test_fetcher_registered():
    assert "elasticache_replication_group" in _FETCHER_REGISTRY


def test_fetch_returns_expected_fields(mock_ec_client):
    mock_ec_client.describe_replication_groups.return_value = {
        "ReplicationGroups": [_make_replication_group()]
    }
    result = fetch_elasticache_replication_group(RG_ID)
    cfg = result.config
    assert cfg["status"] == "available"
    assert cfg["at_rest_encryption"] is True
    assert cfg["transit_encryption"] is True
    assert cfg["num_node_groups"] == 1
    assert cfg["num_replicas_per_node_group"] == 2
    assert cfg["cache_node_type"] == "cache.r6g.large"
    assert cfg["snapshot_retention_limit"] == 7


def test_group_not_found_returns_empty_config(mock_ec_client):
    mock_ec_client.describe_replication_groups.return_value = {
        "ReplicationGroups": []
    }
    result = fetch_elasticache_replication_group(RG_ID)
    assert result.config == {}
    assert result.resource_id == RG_ID


def test_encryption_defaults_to_false(mock_ec_client):
    rg = _make_replication_group(
        AtRestEncryptionEnabled=False,
        TransitEncryptionEnabled=False,
        AuthTokenEnabled=False,
    )
    mock_ec_client.describe_replication_groups.return_value = {
        "ReplicationGroups": [rg]
    }
    result = fetch_elasticache_replication_group(RG_ID)
    assert result.config["at_rest_encryption"] is False
    assert result.config["transit_encryption"] is False
    assert result.config["auth_token_enabled"] is False


def test_region_passed_to_client():
    with patch(
        "driftwatch.fetchers.elasticache._get_elasticache_client"
    ) as mock_factory:
        client = MagicMock()
        client.describe_replication_groups.return_value = {
            "ReplicationGroups": [_make_replication_group()]
        }
        mock_factory.return_value = client
        fetch_elasticache_replication_group(RG_ID, region="eu-west-1")
        mock_factory.assert_called_once_with("eu-west-1")

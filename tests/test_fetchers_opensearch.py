"""Tests for the OpenSearch domain fetcher."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.fetchers.opensearch import fetch_opensearch_domain
from driftwatch.poller import _fetcher_registry


def _make_domain_status(
    engine_version: str = "OpenSearch_2.11",
    instance_type: str = "t3.small.search",
    instance_count: int = 2,
    dedicated_master: bool = False,
    zone_awareness: bool = True,
    ebs_enabled: bool = True,
    volume_type: str = "gp3",
    volume_size: int = 20,
    encrypt_at_rest: bool = True,
    node_to_node: bool = True,
) -> dict:
    return {
        "DomainStatus": {
            "EngineVersion": engine_version,
            "ClusterConfig": {
                "InstanceType": instance_type,
                "InstanceCount": instance_count,
                "DedicatedMasterEnabled": dedicated_master,
                "ZoneAwarenessEnabled": zone_awareness,
            },
            "EBSOptions": {
                "EBSEnabled": ebs_enabled,
                "VolumeType": volume_type,
                "VolumeSize": volume_size,
            },
            "EncryptionAtRestOptions": {"Enabled": encrypt_at_rest},
            "NodeToNodeEncryptionOptions": {"Enabled": node_to_node},
            "AdvancedOptions": {
                "rest.action.multi.allow_explicit_index": "true"
            },
        }
    }


@pytest.fixture()
def mock_opensearch_client():
    with patch("driftwatch.fetchers.opensearch._get_opensearch_client") as mock_factory:
        client = MagicMock()
        mock_factory.return_value = client
        yield client


def test_fetcher_registered():
    assert "opensearch_domain" in _fetcher_registry


def test_fetch_returns_expected_fields(mock_opensearch_client):
    mock_opensearch_client.describe_domain.return_value = _make_domain_status()

    result = fetch_opensearch_domain("my-search-domain")

    assert result.success is True
    assert result.resource_id == "my-search-domain"
    assert result.resource_type == "opensearch_domain"
    cfg = result.config
    assert cfg["engine_version"] == "OpenSearch_2.11"
    assert cfg["instance_type"] == "t3.small.search"
    assert cfg["instance_count"] == 2
    assert cfg["zone_awareness_enabled"] is True
    assert cfg["encrypt_at_rest"] is True
    assert cfg["node_to_node_encryption"] is True
    assert cfg["volume_type"] == "gp3"
    assert cfg["volume_size"] == 20


def test_domain_not_found_returns_empty_config(mock_opensearch_client):
    not_found = mock_opensearch_client.exceptions.ResourceNotFoundException
    mock_opensearch_client.describe_domain.side_effect = not_found()

    result = fetch_opensearch_domain("nonexistent-domain")

    assert result.success is True
    assert result.config == {}


def test_region_passed_to_client():
    with patch("driftwatch.fetchers.opensearch._get_opensearch_client") as mock_factory:
        client = MagicMock()
        client.describe_domain.return_value = _make_domain_status()
        mock_factory.return_value = client

        fetch_opensearch_domain("my-domain", region="eu-west-1")

        mock_factory.assert_called_once_with("eu-west-1")


def test_missing_optional_fields_use_defaults(mock_opensearch_client):
    mock_opensearch_client.describe_domain.return_value = {
        "DomainStatus": {
            "EngineVersion": "OpenSearch_1.3",
            "ClusterConfig": {},
            "EBSOptions": {},
            "EncryptionAtRestOptions": {},
            "NodeToNodeEncryptionOptions": {},
            "AdvancedOptions": {},
        }
    }

    result = fetch_opensearch_domain("bare-domain")

    assert result.success is True
    assert result.config["instance_count"] == 1
    assert result.config["dedicated_master_enabled"] is False
    assert result.config["ebs_enabled"] is False
    assert result.config["encrypt_at_rest"] is False
    assert result.config["node_to_node_encryption"] is False

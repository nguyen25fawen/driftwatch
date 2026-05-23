"""Tests for the RDS instance fetcher."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.fetchers.rds import fetch_rds_instance
from driftwatch.poller import _FETCHER_REGISTRY


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db_instance(**overrides) -> dict:
    base = {
        "DBInstanceIdentifier": "my-db",
        "DBInstanceClass": "db.t3.micro",
        "Engine": "mysql",
        "EngineVersion": "8.0.32",
        "MultiAZ": False,
        "StorageEncrypted": True,
        "PubliclyAccessible": False,
        "DeletionProtection": True,
        "BackupRetentionPeriod": 7,
        "DBSubnetGroup": {"DBSubnetGroupName": "default"},
        "VpcSecurityGroups": [
            {"VpcSecurityGroupId": "sg-abc123", "Status": "active"}
        ],
        "TagList": [{"Key": "Environment", "Value": "staging"}],
    }
    base.update(overrides)
    return base


def _make_describe_response(instance: dict) -> dict:
    return {"DBInstances": [instance]}


@pytest.fixture()
def mock_rds_client():
    with patch("driftwatch.fetchers.rds._get_rds_client") as mock_factory:
        client = MagicMock()
        mock_factory.return_value = client
        client.describe_db_instances.return_value = _make_describe_response(
            _make_db_instance()
        )
        yield client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_fetcher_registered():
    assert "rds_instance" in _FETCHER_REGISTRY


def test_fetch_returns_expected_fields(mock_rds_client):
    result = fetch_rds_instance("my-db", "us-east-1")

    assert result["db_instance_identifier"] == "my-db"
    assert result["db_instance_class"] == "db.t3.micro"
    assert result["engine"] == "mysql"
    assert result["engine_version"] == "8.0.32"
    assert result["multi_az"] is False
    assert result["storage_encrypted"] is True
    assert result["publicly_accessible"] is False
    assert result["deletion_protection"] is True
    assert result["backup_retention_period"] == 7
    assert result["subnet_group"] == "default"
    assert result["security_group_ids"] == ["sg-abc123"]
    assert result["tags"] == {"Environment": "staging"}


def test_fetch_multiple_security_groups(mock_rds_client):
    instance = _make_db_instance(
        VpcSecurityGroups=[
            {"VpcSecurityGroupId": "sg-111", "Status": "active"},
            {"VpcSecurityGroupId": "sg-222", "Status": "active"},
        ]
    )
    mock_rds_client.describe_db_instances.return_value = _make_describe_response(instance)
    result = fetch_rds_instance("my-db", "us-east-1")
    assert sorted(result["security_group_ids"]) == ["sg-111", "sg-222"]


def test_fetch_no_tags(mock_rds_client):
    instance = _make_db_instance(TagList=[])
    mock_rds_client.describe_db_instances.return_value = _make_describe_response(instance)
    result = fetch_rds_instance("my-db", "us-east-1")
    assert result["tags"] == {}

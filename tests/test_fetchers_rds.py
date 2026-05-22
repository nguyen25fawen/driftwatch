"""Tests for driftwatch/fetchers/rds.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from driftwatch.fetchers.rds import fetch_rds_instance
from driftwatch.poller import _FETCHER_REGISTRY


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db_instance(**overrides):
    base = {
        "DBInstanceIdentifier": "prod-mysql-01",
        "DBInstanceClass": "db.t3.medium",
        "Engine": "mysql",
        "EngineVersion": "8.0.32",
        "MultiAZ": True,
        "PubliclyAccessible": False,
        "StorageEncrypted": True,
        "DeletionProtection": True,
        "BackupRetentionPeriod": 7,
        "DBSubnetGroup": {"DBSubnetGroupName": "prod-db-subnet-group"},
    }
    base.update(overrides)
    return base


def _make_describe_response(instance_dict):
    return {"DBInstances": [instance_dict]}


@pytest.fixture()
def mock_rds_client():
    with patch("driftwatch.fetchers.rds._get_rds_client") as mock_factory:
        client = MagicMock()
        mock_factory.return_value = client
        yield client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_fetcher_registered():
    assert "rds_instance" in _FETCHER_REGISTRY


def test_fetch_returns_expected_fields(mock_rds_client):
    inst = _make_db_instance()
    mock_rds_client.describe_db_instances.return_value = _make_describe_response(inst)

    result = fetch_rds_instance("prod-mysql-01", region="us-east-1")

    assert result["db_instance_class"] == "db.t3.medium"
    assert result["engine"] == "mysql"
    assert result["multi_az"] is True
    assert result["publicly_accessible"] is False
    assert result["storage_encrypted"] is True
    assert result["deletion_protection"] is True
    assert result["backup_retention_period"] == 7
    assert result["db_subnet_group"] == "prod-db-subnet-group"


def test_fetch_not_found_raises(mock_rds_client):
    mock_rds_client.describe_db_instances.return_value = {"DBInstances": []}

    with pytest.raises(ValueError, match="not found"):
        fetch_rds_instance("missing-db", region="us-east-1")


def test_fetch_client_error_raises(mock_rds_client):
    mock_rds_client.describe_db_instances.side_effect = ClientError(
        {"Error": {"Code": "DBInstanceNotFound", "Message": "not found"}},
        "DescribeDBInstances",
    )

    with pytest.raises(ValueError, match="Failed to describe RDS instance"):
        fetch_rds_instance("bad-db", region="us-east-1")


def test_fetch_missing_subnet_group(mock_rds_client):
    inst = _make_db_instance()
    del inst["DBSubnetGroup"]
    mock_rds_client.describe_db_instances.return_value = _make_describe_response(inst)

    result = fetch_rds_instance("prod-mysql-01")
    assert result["db_subnet_group"] is None

"""Tests for the Kinesis stream fetcher."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.fetchers.kinesis import fetch_kinesis_stream
from driftwatch.poller import _FETCHER_REGISTRY


def _make_stream_summary(
    name: str = "my-event-stream",
    status: str = "ACTIVE",
    shard_count: int = 2,
    retention: int = 24,
    encryption: str = "KMS",
    key_id: str = "alias/aws/kinesis",
    enhanced: list | None = None,
) -> dict:
    return {
        "StreamDescriptionSummary": {
            "StreamName": name,
            "StreamStatus": status,
            "OpenShardCount": shard_count,
            "RetentionPeriodHours": retention,
            "EncryptionType": encryption,
            "KeyId": key_id,
            "EnhancedMonitoring": enhanced or [],
        }
    }


@pytest.fixture()
def mock_kinesis_client():
    with patch("driftwatch.fetchers.kinesis._get_kinesis_client") as mock_factory:
        client = MagicMock()
        mock_factory.return_value = client
        yield client


def test_fetcher_registered():
    assert "kinesis_stream" in _FETCHER_REGISTRY


def test_fetch_returns_expected_fields(mock_kinesis_client):
    mock_kinesis_client.describe_stream_summary.return_value = _make_stream_summary()

    result = fetch_kinesis_stream("my-event-stream")

    assert result.resource_id == "my-event-stream"
    assert result.resource_type == "kinesis_stream"
    assert result.config["stream_name"] == "my-event-stream"
    assert result.config["stream_status"] == "ACTIVE"
    assert result.config["shard_count"] == 2
    assert result.config["retention_period_hours"] == 24
    assert result.config["encryption_type"] == "KMS"
    assert result.config["key_id"] == "alias/aws/kinesis"
    assert result.config["enhanced_monitoring"] == []


def test_stream_not_found_returns_empty_config(mock_kinesis_client):
    mock_kinesis_client.exceptions.ResourceNotFoundException = Exception
    mock_kinesis_client.describe_stream_summary.side_effect = Exception("not found")

    result = fetch_kinesis_stream("missing-stream")

    assert result.resource_id == "missing-stream"
    assert result.config == {}


def test_enhanced_monitoring_sorted(mock_kinesis_client):
    summary = _make_stream_summary(
        enhanced=[
            {"ShardLevelMetrics": ["WriteProvisionedThroughputExceeded"]},
            {"ShardLevelMetrics": ["IncomingBytes"]},
        ]
    )
    mock_kinesis_client.describe_stream_summary.return_value = summary

    result = fetch_kinesis_stream("my-event-stream")

    metrics = result.config["enhanced_monitoring"]
    assert metrics == sorted(metrics)


def test_missing_encryption_defaults_to_none(mock_kinesis_client):
    raw = _make_stream_summary()
    del raw["StreamDescriptionSummary"]["EncryptionType"]
    del raw["StreamDescriptionSummary"]["KeyId"]
    mock_kinesis_client.describe_stream_summary.return_value = raw

    result = fetch_kinesis_stream("my-event-stream")

    assert result.config["encryption_type"] == "NONE"
    assert result.config["key_id"] == ""

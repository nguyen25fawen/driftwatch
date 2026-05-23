"""Tests for the SQS queue fetcher."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.fetchers.sqs import fetch_sqs_queue
from driftwatch.poller import _FETCHER_REGISTRY

QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/123456789012/my-queue"


def _make_attrs(
    visibility_timeout="30",
    max_message_size="262144",
    message_retention="345600",
    delay_seconds="0",
    wait_time="0",
    fifo="false",
    dedup="false",
    kms_key="",
    policy="",
) -> dict:
    attrs: dict = {
        "VisibilityTimeout": visibility_timeout,
        "MaximumMessageSize": max_message_size,
        "MessageRetentionPeriod": message_retention,
        "DelaySeconds": delay_seconds,
        "ReceiveMessageWaitTimeSeconds": wait_time,
        "FifoQueue": fifo,
        "ContentBasedDeduplication": dedup,
    }
    if kms_key:
        attrs["KmsMasterKeyId"] = kms_key
    if policy:
        attrs["Policy"] = policy
    return attrs


@pytest.fixture()
def mock_sqs_client():
    with patch("driftwatch.fetchers.sqs._get_sqs_client") as mock_get:
        client = MagicMock()
        mock_get.return_value = client
        yield client


def test_fetcher_registered():
    assert "sqs_queue" in _FETCHER_REGISTRY


def test_fetch_returns_expected_fields(mock_sqs_client):
    mock_sqs_client.get_queue_attributes.return_value = {"Attributes": _make_attrs()}
    result = fetch_sqs_queue(QUEUE_URL)
    assert result.success is True
    assert result.resource_id == QUEUE_URL
    assert result.resource_type == "sqs_queue"
    cfg = result.config
    assert cfg["visibility_timeout"] == 30
    assert cfg["max_message_size"] == 262144
    assert cfg["message_retention_seconds"] == 345600
    assert cfg["delay_seconds"] == 0
    assert cfg["receive_wait_time_seconds"] == 0


def test_fifo_and_dedup_parsed_as_bool(mock_sqs_client):
    mock_sqs_client.get_queue_attributes.return_value = {
        "Attributes": _make_attrs(fifo="true", dedup="true")
    }
    result = fetch_sqs_queue(QUEUE_URL)
    assert result.config["fifo_queue"] is True
    assert result.config["content_based_deduplication"] is True


def test_kms_key_included(mock_sqs_client):
    mock_sqs_client.get_queue_attributes.return_value = {
        "Attributes": _make_attrs(kms_key="alias/my-key")
    }
    result = fetch_sqs_queue(QUEUE_URL)
    assert result.config["kms_master_key_id"] == "alias/my-key"


def test_missing_attributes_default_to_zero(mock_sqs_client):
    mock_sqs_client.get_queue_attributes.return_value = {"Attributes": {}}
    result = fetch_sqs_queue(QUEUE_URL)
    assert result.success is True
    assert result.config["visibility_timeout"] == 0
    assert result.config["fifo_queue"] is False

"""Integration-style tests verifying SQS fetcher output maps to baseline schema."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from driftwatch.baseline import load_baselines
from driftwatch.detector import detect_drift
from driftwatch.fetchers.sqs import fetch_sqs_queue

BASELINE_PATH = Path("driftwatch/baselines/example_sqs_baseline.json")
QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/123456789012/my-queue"


@pytest.fixture()
def mock_sqs_client():
    with patch("driftwatch.fetchers.sqs._get_sqs_client") as mock_get:
        client = MagicMock()
        mock_get.return_value = client
        yield client


def _matching_attrs() -> dict:
    return {
        "VisibilityTimeout": "30",
        "MaximumMessageSize": "262144",
        "MessageRetentionPeriod": "345600",
        "DelaySeconds": "0",
        "ReceiveMessageWaitTimeSeconds": "0",
        "FifoQueue": "false",
        "ContentBasedDeduplication": "false",
        "KmsMasterKeyId": "",
        "Policy": "",
    }


def test_example_baseline_loads():
    """Ensure the example SQS baseline file is valid and parseable."""
    baselines = load_baselines(str(BASELINE_PATH))
    assert len(baselines) == 1
    bl = baselines[0]
    assert bl.resource_type == "sqs_queue"
    assert "visibility_timeout" in bl.expected_config


def test_no_drift_against_example_baseline(mock_sqs_client):
    """Fetched config matching the baseline should produce no drift."""
    mock_sqs_client.get_queue_attributes.return_value = {"Attributes": _matching_attrs()}
    baselines = load_baselines(str(BASELINE_PATH))
    result = fetch_sqs_queue(QUEUE_URL)
    drift = detect_drift(result, baselines[0])
    assert drift.has_drift is False
    assert drift.drifted_keys == []


def test_drift_detected_on_visibility_change(mock_sqs_client):
    """Changing visibility_timeout should be flagged as drift."""
    attrs = _matching_attrs()
    attrs["VisibilityTimeout"] = "60"  # differs from baseline value of 30
    mock_sqs_client.get_queue_attributes.return_value = {"Attributes": attrs}
    baselines = load_baselines(str(BASELINE_PATH))
    result = fetch_sqs_queue(QUEUE_URL)
    drift = detect_drift(result, baselines[0])
    assert drift.has_drift is True
    assert "visibility_timeout" in drift.drifted_keys


def test_drift_detected_on_multiple_changes(mock_sqs_client):
    """Changing multiple attributes should report all drifted keys."""
    attrs = _matching_attrs()
    attrs["VisibilityTimeout"] = "60"  # differs from baseline value of 30
    attrs["DelaySeconds"] = "10"  # differs from baseline value of 0
    mock_sqs_client.get_queue_attributes.return_value = {"Attributes": attrs}
    baselines = load_baselines(str(BASELINE_PATH))
    result = fetch_sqs_queue(QUEUE_URL)
    drift = detect_drift(result, baselines[0])
    assert drift.has_drift is True
    assert "visibility_timeout" in drift.drifted_keys
    assert "delay_seconds" in drift.drifted_keys

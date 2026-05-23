"""Tests for the CloudWatch alarm fetcher."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.fetchers.cloudwatch import fetch_cloudwatch_alarm
from driftwatch.poller import _FETCHER_REGISTRY


ALARM_NAME = "high-cpu-alarm"


def _make_alarm(**overrides: object) -> dict:
    base = {
        "AlarmName": ALARM_NAME,
        "AlarmDescription": "CPU utilisation too high",
        "MetricName": "CPUUtilization",
        "Namespace": "AWS/EC2",
        "Statistic": "Average",
        "ComparisonOperator": "GreaterThanThreshold",
        "Threshold": 80.0,
        "EvaluationPeriods": 2,
        "Period": 300,
        "TreatMissingData": "notBreaching",
        "ActionsEnabled": True,
        "AlarmActions": ["arn:aws:sns:us-east-1:123456789012:alerts"],
        "OKActions": [],
        "InsufficientDataActions": [],
    }
    base.update(overrides)
    return base


@pytest.fixture()
def mock_cloudwatch_client(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    client = MagicMock()
    monkeypatch.setattr(
        "driftwatch.fetchers.cloudwatch._get_cloudwatch_client",
        lambda region=None: client,
    )
    return client


def test_fetcher_registered() -> None:
    assert "cloudwatch_alarm" in _FETCHER_REGISTRY


def test_fetch_returns_expected_fields(
    mock_cloudwatch_client: MagicMock,
) -> None:
    mock_cloudwatch_client.describe_alarms.return_value = {
        "MetricAlarms": [_make_alarm()]
    }
    result = fetch_cloudwatch_alarm(ALARM_NAME)
    assert result.resource_id == ALARM_NAME
    assert result.error is None
    cfg = result.config
    assert cfg["metric_name"] == "CPUUtilization"
    assert cfg["threshold"] == 80.0
    assert cfg["treat_missing_data"] == "notBreaching"
    assert cfg["alarm_actions"] == ["arn:aws:sns:us-east-1:123456789012:alerts"]


def test_alarm_actions_sorted(
    mock_cloudwatch_client: MagicMock,
) -> None:
    alarm = _make_alarm(
        AlarmActions=[
            "arn:aws:sns:us-east-1:123456789012:z-topic",
            "arn:aws:sns:us-east-1:123456789012:a-topic",
        ]
    )
    mock_cloudwatch_client.describe_alarms.return_value = {"MetricAlarms": [alarm]}
    result = fetch_cloudwatch_alarm(ALARM_NAME)
    assert result.config["alarm_actions"] == [
        "arn:aws:sns:us-east-1:123456789012:a-topic",
        "arn:aws:sns:us-east-1:123456789012:z-topic",
    ]


def test_alarm_not_found_returns_error(
    mock_cloudwatch_client: MagicMock,
) -> None:
    mock_cloudwatch_client.describe_alarms.return_value = {"MetricAlarms": []}
    result = fetch_cloudwatch_alarm("nonexistent-alarm")
    assert result.error is not None
    assert "not found" in result.error


def test_client_exception_returns_error(
    mock_cloudwatch_client: MagicMock,
) -> None:
    mock_cloudwatch_client.describe_alarms.side_effect = RuntimeError("network error")
    result = fetch_cloudwatch_alarm(ALARM_NAME)
    assert result.error == "network error"
    assert result.config == {}

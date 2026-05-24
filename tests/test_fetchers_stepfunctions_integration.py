"""Integration tests: Step Functions fetcher against example baseline."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from driftwatch.baseline import load_baselines
from driftwatch.detector import detect_drift
from driftwatch.fetchers.stepfunctions import fetch_stepfunctions_statemachine

BASELINE_PATH = (
    Path(__file__).parent.parent
    / "driftwatch"
    / "baselines"
    / "example_stepfunctions_baseline.json"
)

ARN = "arn:aws:states:us-east-1:123456789012:stateMachine:MyStateMachine"


def _matching_response():
    return {
        "stateMachineArn": ARN,
        "name": "MyStateMachine",
        "type": "STANDARD",
        "status": "ACTIVE",
        "roleArn": "arn:aws:iam::123456789012:role/StepFunctionsRole",
        "loggingConfiguration": {"level": "ERROR"},
        "tracingConfiguration": {"enabled": True},
    }


@pytest.fixture()
def mock_sfn_client():
    with patch(
        "driftwatch.fetchers.stepfunctions._get_sfn_client"
    ) as mock_factory:
        client = MagicMock()
        mock_factory.return_value = client
        yield client


def test_example_baseline_loads():
    baselines = load_baselines(str(BASELINE_PATH))
    assert len(baselines) == 1
    assert baselines[0].resource_type == "stepfunctions"


def test_no_drift_against_example_baseline(mock_sfn_client):
    mock_sfn_client.describe_state_machine.return_value = _matching_response()
    baselines = load_baselines(str(BASELINE_PATH))
    baseline = baselines[0]

    poll = fetch_stepfunctions_statemachine(baseline.resource_id, region=baseline.region)
    result = detect_drift(baseline, poll.config)

    assert not result.has_drift


def test_drift_detected_on_type_change(mock_sfn_client):
    resp = _matching_response()
    resp["type"] = "EXPRESS"
    mock_sfn_client.describe_state_machine.return_value = resp

    baselines = load_baselines(str(BASELINE_PATH))
    baseline = baselines[0]

    poll = fetch_stepfunctions_statemachine(baseline.resource_id, region=baseline.region)
    result = detect_drift(baseline, poll.config)

    assert result.has_drift
    assert "type" in result.drifted_keys


def test_drift_detected_on_tracing_disabled(mock_sfn_client):
    resp = _matching_response()
    resp["tracingConfiguration"] = {"enabled": False}
    mock_sfn_client.describe_state_machine.return_value = resp

    baselines = load_baselines(str(BASELINE_PATH))
    baseline = baselines[0]

    poll = fetch_stepfunctions_statemachine(baseline.resource_id, region=baseline.region)
    result = detect_drift(baseline, poll.config)

    assert result.has_drift
    assert "tracing_enabled" in result.drifted_keys

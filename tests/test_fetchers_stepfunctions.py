"""Unit tests for the Step Functions fetcher."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.poller import _FETCHER_REGISTRY
from driftwatch.fetchers.stepfunctions import fetch_stepfunctions_statemachine

ARN = "arn:aws:states:us-east-1:123456789012:stateMachine:MyStateMachine"


def _make_state_machine(**overrides):
    base = {
        "stateMachineArn": ARN,
        "name": "MyStateMachine",
        "type": "STANDARD",
        "status": "ACTIVE",
        "roleArn": "arn:aws:iam::123456789012:role/StepFunctionsRole",
        "loggingConfiguration": {"level": "ERROR"},
        "tracingConfiguration": {"enabled": True},
    }
    base.update(overrides)
    return base


@pytest.fixture()
def mock_sfn_client():
    with patch(
        "driftwatch.fetchers.stepfunctions._get_sfn_client"
    ) as mock_factory:
        client = MagicMock()
        mock_factory.return_value = client
        yield client


def test_fetcher_registered():
    assert "stepfunctions" in _FETCHER_REGISTRY


def test_fetch_returns_expected_fields(mock_sfn_client):
    mock_sfn_client.describe_state_machine.return_value = _make_state_machine()

    result = fetch_stepfunctions_statemachine(ARN, region="us-east-1")

    assert result.resource_id == ARN
    assert result.config["name"] == "MyStateMachine"
    assert result.config["type"] == "STANDARD"
    assert result.config["status"] == "ACTIVE"
    assert result.config["logging_level"] == "ERROR"
    assert result.config["tracing_enabled"] is True


def test_tracing_defaults_to_false(mock_sfn_client):
    sm = _make_state_machine()
    del sm["tracingConfiguration"]
    mock_sfn_client.describe_state_machine.return_value = sm

    result = fetch_stepfunctions_statemachine(ARN)

    assert result.config["tracing_enabled"] is False


def test_logging_defaults_to_off(mock_sfn_client):
    sm = _make_state_machine()
    del sm["loggingConfiguration"]
    mock_sfn_client.describe_state_machine.return_value = sm

    result = fetch_stepfunctions_statemachine(ARN)

    assert result.config["logging_level"] == "OFF"


def test_state_machine_not_found_returns_empty(mock_sfn_client):
    mock_sfn_client.exceptions.StateMachineDoesNotExist = type(
        "StateMachineDoesNotExist", (Exception,), {}
    )
    mock_sfn_client.describe_state_machine.side_effect = (
        mock_sfn_client.exceptions.StateMachineDoesNotExist("not found")
    )

    result = fetch_stepfunctions_statemachine(ARN)

    assert result.config == {}


def test_region_forwarded_to_client():
    with patch(
        "driftwatch.fetchers.stepfunctions._get_sfn_client"
    ) as mock_factory:
        client = MagicMock()
        client.describe_state_machine.return_value = _make_state_machine()
        mock_factory.return_value = client

        fetch_stepfunctions_statemachine(ARN, region="eu-west-1")

        mock_factory.assert_called_once_with("eu-west-1")

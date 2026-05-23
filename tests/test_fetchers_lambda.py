"""Tests for the Lambda fetcher."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

import driftwatch.fetchers.lambda_  # noqa: F401 — ensure registration side-effect
from driftwatch.poller import _FETCHER_REGISTRY


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_function_config(**overrides: object) -> dict:
    base = {
        "FunctionName": "my-function",
        "Runtime": "python3.12",
        "Handler": "handler.main",
        "Timeout": 30,
        "MemorySize": 256,
        "Role": "arn:aws:iam::123456789012:role/lambda-role",
        "Description": "A test function",
        "TracingConfig": {"Mode": "Active"},
        "Environment": {"Variables": {"LOG_LEVEL": "INFO"}},
        "Layers": [{"Arn": "arn:aws:lambda:us-east-1:123456789012:layer:my-layer:1"}],
        "PackageType": "Zip",
        "Architectures": ["x86_64"],
    }
    base.update(overrides)
    return base


@pytest.fixture()
def mock_lambda_client(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(
        "driftwatch.fetchers.lambda_._get_lambda_client",
        lambda region: client,
    )
    return client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_fetcher_registered():
    assert "lambda" in _FETCHER_REGISTRY


def test_fetch_returns_expected_fields(mock_lambda_client):
    mock_lambda_client.get_function_configuration.return_value = _make_function_config()

    from driftwatch.fetchers.lambda_ import fetch_lambda_function

    result = fetch_lambda_function("my-function", region="us-east-1")

    assert result["function_name"] == "my-function"
    assert result["runtime"] == "python3.12"
    assert result["timeout"] == 30
    assert result["memory_size"] == 256
    assert result["tracing_mode"] == "Active"
    assert result["environment_variables"] == {"LOG_LEVEL": "INFO"}
    assert "arn:aws:lambda:us-east-1:123456789012:layer:my-layer:1" in result["layers"]


def test_layers_sorted(mock_lambda_client):
    cfg = _make_function_config(
        Layers=[
            {"Arn": "arn:aws:lambda:::layer:b:2"},
            {"Arn": "arn:aws:lambda:::layer:a:1"},
        ]
    )
    mock_lambda_client.get_function_configuration.return_value = cfg

    from driftwatch.fetchers.lambda_ import fetch_lambda_function

    result = fetch_lambda_function("my-function")
    assert result["layers"] == sorted(result["layers"])


def test_missing_environment_defaults_to_empty(mock_lambda_client):
    cfg = _make_function_config()
    cfg.pop("Environment", None)
    mock_lambda_client.get_function_configuration.return_value = cfg

    from driftwatch.fetchers.lambda_ import fetch_lambda_function

    result = fetch_lambda_function("my-function")
    assert result["environment_variables"] == {}


def test_client_error_propagates(mock_lambda_client):
    mock_lambda_client.get_function_configuration.side_effect = ClientError(
        {"Error": {"Code": "ResourceNotFoundException", "Message": "not found"}},
        "GetFunctionConfiguration",
    )

    from driftwatch.fetchers.lambda_ import fetch_lambda_function

    with pytest.raises(ClientError):
        fetch_lambda_function("missing-function")

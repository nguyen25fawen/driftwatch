"""Tests for the Secrets Manager fetcher."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.fetchers.secretsmanager import fetch_secretsmanager_secret
from driftwatch.poller import _FETCHER_REGISTRY


SECRET_ID = "prod/myapp/database"


def _make_describe_response(
    rotation_enabled: bool = True,
    rotation_arn: str = "arn:aws:lambda:us-east-1:123:function:Rotate",
    tags: list[dict] | None = None,
) -> dict:
    return {
        "Name": SECRET_ID,
        "Description": "Production database credentials",
        "KmsKeyId": "alias/aws/secretsmanager",
        "RotationEnabled": rotation_enabled,
        "RotationLambdaARN": rotation_arn,
        "RotationRules": {"AutomaticallyAfterDays": 30},
        "Tags": tags or [{"Key": "Environment", "Value": "production"}],
    }


@pytest.fixture()
def mock_sm_client():
    with patch(
        "driftwatch.fetchers.secretsmanager._get_secretsmanager_client"
    ) as factory:
        client = MagicMock()
        factory.return_value = client
        yield client


def test_fetcher_registered():
    assert "secretsmanager_secret" in _FETCHER_REGISTRY


def test_fetch_returns_expected_fields(mock_sm_client):
    mock_sm_client.describe_secret.return_value = _make_describe_response()

    result = fetch_secretsmanager_secret(SECRET_ID, region="us-east-1")

    assert result.resource_id == SECRET_ID
    assert result.resource_type == "secretsmanager_secret"
    cfg = result.config
    assert cfg["name"] == SECRET_ID
    assert cfg["rotation_enabled"] is True
    assert cfg["automatically_after_days"] == 30
    assert cfg["tags"] == {"Environment": "production"}


def test_rotation_disabled(mock_sm_client):
    mock_sm_client.describe_secret.return_value = _make_describe_response(
        rotation_enabled=False, rotation_arn=""
    )

    result = fetch_secretsmanager_secret(SECRET_ID)
    assert result.config["rotation_enabled"] is False
    assert result.config["rotation_lambda_arn"] == ""


def test_missing_secret_returns_empty_config(mock_sm_client):
    not_found = mock_sm_client.exceptions.ResourceNotFoundException
    mock_sm_client.describe_secret.side_effect = not_found()

    result = fetch_secretsmanager_secret("nonexistent/secret")
    assert result.config == {}


def test_tags_converted_to_dict(mock_sm_client):
    tags = [
        {"Key": "Env", "Value": "prod"},
        {"Key": "Team", "Value": "platform"},
    ]
    mock_sm_client.describe_secret.return_value = _make_describe_response(
        tags=tags
    )

    result = fetch_secretsmanager_secret(SECRET_ID)
    assert result.config["tags"] == {"Env": "prod", "Team": "platform"}


def test_no_rotation_rules_defaults_to_zero(mock_sm_client):
    resp = _make_describe_response()
    resp.pop("RotationRules", None)
    mock_sm_client.describe_secret.return_value = resp

    result = fetch_secretsmanager_secret(SECRET_ID)
    assert result.config["automatically_after_days"] == 0

"""Tests for the API Gateway REST API fetcher."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.fetchers.apigateway import fetch_apigateway_rest_api
from driftwatch.poller import _FETCHER_REGISTRY


API_ID = "abc123xyz"


def _make_api(**overrides):
    base = {
        "id": API_ID,
        "name": "my-rest-api",
        "description": "Production REST API",
        "apiKeySource": "HEADER",
        "endpointConfiguration": {"types": ["REGIONAL"]},
        "minimumCompressionSize": None,
        "disableExecuteApiEndpoint": False,
    }
    base.update(overrides)
    return base


def _make_stages(*names):
    return {"item": [{"stageName": n} for n in names]}


@pytest.fixture()
def mock_apigw_client():
    with patch("driftwatch.fetchers.apigateway._get_apigw_client") as mock_factory:
        client = MagicMock()
        client.exceptions.NotFoundException = type("NotFoundException", (Exception,), {})
        mock_factory.return_value = client
        yield client


def test_fetcher_registered():
    assert "apigateway_rest_api" in _FETCHER_REGISTRY


def test_fetch_returns_expected_fields(mock_apigw_client):
    mock_apigw_client.get_rest_api.return_value = _make_api()
    mock_apigw_client.get_stages.return_value = _make_stages("prod", "staging")

    result = fetch_apigateway_rest_api(API_ID)

    assert result.resource_id == API_ID
    assert result.resource_type == "apigateway_rest_api"
    assert result.config["name"] == "my-rest-api"
    assert result.config["endpoint_types"] == ["REGIONAL"]
    assert result.config["stages"] == ["prod", "staging"]
    assert result.config["api_key_source"] == "HEADER"
    assert result.config["disable_execute_api_endpoint"] is False


def test_stages_are_sorted(mock_apigw_client):
    mock_apigw_client.get_rest_api.return_value = _make_api()
    mock_apigw_client.get_stages.return_value = _make_stages("staging", "prod", "dev")

    result = fetch_apigateway_rest_api(API_ID)

    assert result.config["stages"] == ["dev", "prod", "staging"]


def test_endpoint_types_sorted(mock_apigw_client):
    mock_apigw_client.get_rest_api.return_value = _make_api(
        endpointConfiguration={"types": ["REGIONAL", "EDGE"]}
    )
    mock_apigw_client.get_stages.return_value = _make_stages()

    result = fetch_apigateway_rest_api(API_ID)

    assert result.config["endpoint_types"] == ["EDGE", "REGIONAL"]


def test_not_found_returns_empty_config(mock_apigw_client):
    mock_apigw_client.get_rest_api.side_effect = (
        mock_apigw_client.exceptions.NotFoundException()
    )

    result = fetch_apigateway_rest_api(API_ID)

    assert result.config == {}
    assert result.resource_id == API_ID


def test_region_forwarded_to_client():
    with patch("driftwatch.fetchers.apigateway._get_apigw_client") as mock_factory:
        client = MagicMock()
        client.exceptions.NotFoundException = type("NotFoundException", (Exception,), {})
        client.get_rest_api.return_value = _make_api()
        client.get_stages.return_value = _make_stages()
        mock_factory.return_value = client

        fetch_apigateway_rest_api(API_ID, region="eu-west-1")

        mock_factory.assert_called_once_with("eu-west-1")

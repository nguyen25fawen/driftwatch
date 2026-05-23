"""Tests for the DynamoDB table fetcher."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.fetchers.dynamodb import fetch_dynamodb_table
from driftwatch.poller import _FETCHER_REGISTRY


def _make_table(
    name: str = "my-app-table",
    billing_mode: str = "PAY_PER_REQUEST",
    sse_status: str = "ENABLED",
    streams_enabled: bool = True,
    stream_view_type: str = "NEW_AND_OLD_IMAGES",
) -> dict:
    table = {
        "TableName": name,
        "TableStatus": "ACTIVE",
        "ItemCount": 42,
        "KeySchema": [
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
        "BillingModeSummary": {"BillingMode": billing_mode},
        "ProvisionedThroughput": {"ReadCapacityUnits": 0, "WriteCapacityUnits": 0},
        "SSEDescription": {"Status": sse_status},
        "StreamSpecification": {
            "StreamEnabled": streams_enabled,
            "StreamViewType": stream_view_type,
        },
    }
    return table


@pytest.fixture()
def mock_dynamodb_client(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(
        "driftwatch.fetchers.dynamodb._get_dynamodb_client", lambda region: client
    )
    return client


def test_fetcher_registered():
    assert "dynamodb_table" in _FETCHER_REGISTRY


def test_fetch_returns_expected_fields(mock_dynamodb_client):
    mock_dynamodb_client.describe_table.return_value = {
        "Table": _make_table()
    }
    result = fetch_dynamodb_table("my-app-table", region="us-east-1")

    assert result["table_name"] == "my-app-table"
    assert result["table_status"] == "ACTIVE"
    assert result["billing_mode"] == "PAY_PER_REQUEST"
    assert result["sse_status"] == "ENABLED"
    assert result["streams_enabled"] is True
    assert result["stream_view_type"] == "NEW_AND_OLD_IMAGES"
    assert result["item_count"] == 42


def test_key_schema_sorted(mock_dynamodb_client):
    """RANGE key should appear after HASH when sorted by KeyType."""
    mock_dynamodb_client.describe_table.return_value = {
        "Table": _make_table()
    }
    result = fetch_dynamodb_table("my-app-table", region="us-east-1")
    key_types = [k["KeyType"] for k in result["key_schema"]]
    assert key_types == sorted(key_types)


def test_missing_billing_summary_defaults_to_provisioned(mock_dynamodb_client):
    table = _make_table()
    del table["BillingModeSummary"]
    mock_dynamodb_client.describe_table.return_value = {"Table": table}

    result = fetch_dynamodb_table("my-app-table", region="us-east-1")
    assert result["billing_mode"] == "PROVISIONED"


def test_missing_sse_defaults_to_disabled(mock_dynamodb_client):
    table = _make_table()
    del table["SSEDescription"]
    mock_dynamodb_client.describe_table.return_value = {"Table": table}

    result = fetch_dynamodb_table("my-app-table", region="us-east-1")
    assert result["sse_status"] == "DISABLED"


def test_missing_stream_spec_defaults_false(mock_dynamodb_client):
    table = _make_table()
    del table["StreamSpecification"]
    mock_dynamodb_client.describe_table.return_value = {"Table": table}

    result = fetch_dynamodb_table("my-app-table", region="us-east-1")
    assert result["streams_enabled"] is False
    assert result["stream_view_type"] is None

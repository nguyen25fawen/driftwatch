"""Tests for the SNS topic fetcher."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from driftwatch.fetchers.sns import fetch_sns_topic
from driftwatch.poller import _FETCHER_REGISTRY

TOPIC_ARN = "arn:aws:sns:us-east-1:123456789012:my-alerts-topic"


def _make_attrs(
    display_name: str = "My Topic",
    kms_key: str = "alias/aws/sns",
    fifo: str = "false",
    dedup: str = "false",
) -> dict:
    policy = json.dumps({"Version": "2012-10-17", "Statement": []})
    return {
        "Attributes": {
            "TopicArn": TOPIC_ARN,
            "DisplayName": display_name,
            "SubscriptionsConfirmed": "3",
            "SubscriptionsPending": "0",
            "KmsMasterKeyId": kms_key,
            "FifoTopic": fifo,
            "ContentBasedDeduplication": dedup,
            "Policy": policy,
        }
    }


@pytest.fixture()
def mock_sns_client():
    with patch("driftwatch.fetchers.sns._get_sns_client") as mock_factory:
        client = MagicMock()
        mock_factory.return_value = client
        yield client


def test_fetcher_registered():
    assert "sns_topic" in _FETCHER_REGISTRY


def test_fetch_returns_expected_fields(mock_sns_client):
    mock_sns_client.get_topic_attributes.return_value = _make_attrs()

    result = fetch_sns_topic(TOPIC_ARN, region="us-east-1")

    assert result["topic_arn"] == TOPIC_ARN
    assert result["display_name"] == "My Topic"
    assert result["subscriptions_confirmed"] == 3
    assert result["subscriptions_pending"] == 0
    assert result["kms_master_key_id"] == "alias/aws/sns"
    assert result["fifo_topic"] is False
    assert result["content_based_deduplication"] is False
    assert isinstance(result["policy"], dict)


def test_fifo_and_dedup_parsed_as_bool(mock_sns_client):
    mock_sns_client.get_topic_attributes.return_value = _make_attrs(
        fifo="true", dedup="true"
    )

    result = fetch_sns_topic(TOPIC_ARN)

    assert result["fifo_topic"] is True
    assert result["content_based_deduplication"] is True


def test_missing_kms_key_defaults_to_empty_string(mock_sns_client):
    attrs = _make_attrs()
    del attrs["Attributes"]["KmsMasterKeyId"]
    mock_sns_client.get_topic_attributes.return_value = attrs

    result = fetch_sns_topic(TOPIC_ARN)

    assert result["kms_master_key_id"] == ""


def test_client_error_propagates(mock_sns_client):
    from botocore.exceptions import ClientError

    mock_sns_client.get_topic_attributes.side_effect = ClientError(
        {"Error": {"Code": "NotFound", "Message": "Topic not found"}},
        "GetTopicAttributes",
    )

    with pytest.raises(ClientError):
        fetch_sns_topic(TOPIC_ARN)


def test_region_passed_to_client_factory(mock_sns_client):
    """Verify that the region argument is forwarded to the client factory."""
    with patch("driftwatch.fetchers.sns._get_sns_client") as mock_factory:
        client = MagicMock()
        mock_factory.return_value = client
        client.get_topic_attributes.return_value = _make_attrs()

        fetch_sns_topic(TOPIC_ARN, region="eu-west-1")

        mock_factory.assert_called_once_with(region="eu-west-1")

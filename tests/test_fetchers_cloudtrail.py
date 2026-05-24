"""Tests for driftwatch/fetchers/cloudtrail.py."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.fetchers.cloudtrail import fetch_cloudtrail_trail
from driftwatch.poller import _FETCHER_REGISTRY


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_trail(
    name: str = "my-trail",
    bucket: str = "my-log-bucket",
    global_events: bool = True,
    multi_region: bool = True,
    log_validation: bool = True,
    kms_key_id: str | None = "arn:aws:kms:us-east-1:123456789012:key/abc",
    log_group_arn: str | None = "arn:aws:logs:us-east-1:123456789012:log-group:CloudTrail",
    has_custom_selectors: bool = True,
) -> dict:
    return {
        "Name": name,
        "S3BucketName": bucket,
        "IncludeGlobalServiceEvents": global_events,
        "IsMultiRegionTrail": multi_region,
        "LogFileValidationEnabled": log_validation,
        "KMSKeyId": kms_key_id,
        "CloudWatchLogsLogGroupArn": log_group_arn,
        "HasCustomEventSelectors": has_custom_selectors,
    }


@pytest.fixture()
def mock_cloudtrail_client():
    with patch("driftwatch.fetchers.cloudtrail._get_cloudtrail_client") as mock_factory:
        client = MagicMock()
        mock_factory.return_value = client

        client.describe_trails.return_value = {"trailList": [_make_trail()]}
        client.get_event_selectors.return_value = {
            "EventSelectors": [
                {"ReadWriteType": "All"},
            ]
        }
        yield client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_fetcher_registered():
    assert "cloudtrail" in _FETCHER_REGISTRY


def test_fetch_returns_expected_fields(mock_cloudtrail_client):
    result = fetch_cloudtrail_trail("my-trail")

    assert result["name"] == "my-trail"
    assert result["s3_bucket_name"] == "my-log-bucket"
    assert result["is_multi_region_trail"] is True
    assert result["log_file_validation_enabled"] is True
    assert result["include_global_service_events"] is True
    assert result["has_custom_event_selectors"] is True
    assert result["event_selector_read_write_types"] == ["All"]


def test_event_selector_types_are_sorted(mock_cloudtrail_client):
    mock_cloudtrail_client.get_event_selectors.return_value = {
        "EventSelectors": [
            {"ReadWriteType": "WriteOnly"},
            {"ReadWriteType": "ReadOnly"},
        ]
    }
    result = fetch_cloudtrail_trail("my-trail")
    assert result["event_selector_read_write_types"] == ["ReadOnly", "WriteOnly"]


def test_trail_not_found_returns_empty(mock_cloudtrail_client):
    mock_cloudtrail_client.describe_trails.return_value = {"trailList": []}
    result = fetch_cloudtrail_trail("nonexistent-trail")
    assert result == {}


def test_describe_trails_client_error_returns_empty(mock_cloudtrail_client):
    from botocore.exceptions import ClientError

    mock_cloudtrail_client.describe_trails.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "denied"}},
        "DescribeTrails",
    )
    result = fetch_cloudtrail_trail("my-trail")
    assert result == {}


def test_event_selectors_error_returns_empty_list(mock_cloudtrail_client):
    from botocore.exceptions import ClientError

    mock_cloudtrail_client.get_event_selectors.side_effect = ClientError(
        {"Error": {"Code": "TrailNotFoundException", "Message": "not found"}},
        "GetEventSelectors",
    )
    result = fetch_cloudtrail_trail("my-trail")
    assert result["event_selector_read_write_types"] == []
    assert result["name"] == "my-trail"

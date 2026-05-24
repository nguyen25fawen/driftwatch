"""Unit tests for the Route53 hosted-zone fetcher."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.fetchers.route53 import fetch_route53_hosted_zone
from driftwatch.poller import _FETCHER_REGISTRY


ZONE_ID = "Z1D633PJN98FT9"


def _make_zone(
    name: str = "example.com.",
    private: bool = False,
    comment: str = "test",
    record_count: int = 3,
) -> dict:
    return {
        "HostedZone": {
            "Id": f"/hostedzone/{ZONE_ID}",
            "Name": name,
            "Config": {"PrivateZone": private, "Comment": comment},
            "ResourceRecordSetCount": record_count,
        },
        "VPCs": [],
    }


@pytest.fixture()
def mock_r53_client():
    with patch("driftwatch.fetchers.route53._get_route53_client") as mock_factory:
        client = MagicMock()
        mock_factory.return_value = client
        yield client


def test_fetcher_registered():
    assert "route53_hosted_zone" in _FETCHER_REGISTRY


def test_fetch_returns_expected_fields(mock_r53_client):
    mock_r53_client.get_hosted_zone.return_value = _make_zone()
    result = fetch_route53_hosted_zone(ZONE_ID, "us-east-1")

    assert result.resource_id == ZONE_ID
    assert result.resource_type == "route53_hosted_zone"
    cfg = result.config
    assert cfg["name"] == "example.com."
    assert cfg["private_zone"] is False
    assert cfg["comment"] == "test"
    assert cfg["record_count"] == 3
    assert cfg["vpcs"] == []


def test_vpcs_sorted(mock_r53_client):
    resp = _make_zone(private=True)
    resp["VPCs"] = [
        {"VPCId": "vpc-zzz", "VPCRegion": "us-east-1"},
        {"VPCId": "vpc-aaa", "VPCRegion": "us-west-2"},
    ]
    mock_r53_client.get_hosted_zone.return_value = resp
    result = fetch_route53_hosted_zone(ZONE_ID, "us-east-1")
    vpc_ids = [v["vpc_id"] for v in result.config["vpcs"]]
    assert vpc_ids == sorted(vpc_ids)


def test_zone_not_found_returns_empty_config(mock_r53_client):
    mock_r53_client.exceptions.NoSuchHostedZone = type("NoSuchHostedZone", (Exception,), {})
    mock_r53_client.get_hosted_zone.side_effect = mock_r53_client.exceptions.NoSuchHostedZone
    result = fetch_route53_hosted_zone("ZNONEXISTENT", "us-east-1")
    assert result.config == {}


def test_private_zone_flag_captured(mock_r53_client):
    mock_r53_client.get_hosted_zone.return_value = _make_zone(private=True)
    result = fetch_route53_hosted_zone(ZONE_ID, "us-east-1")
    assert result.config["private_zone"] is True


def test_missing_comment_defaults_to_empty_string(mock_r53_client):
    """Zones created without a comment omit the 'Comment' key; verify graceful handling."""
    resp = _make_zone()
    del resp["HostedZone"]["Config"]["Comment"]
    mock_r53_client.get_hosted_zone.return_value = resp
    result = fetch_route53_hosted_zone(ZONE_ID, "us-east-1")
    assert result.config["comment"] == ""

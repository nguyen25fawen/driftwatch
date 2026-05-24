"""Tests for driftwatch/fetchers/cloudfront.py."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.fetchers.cloudfront import fetch_cloudfront_distribution
from driftwatch.poller import _FETCHER_REGISTRY


DIST_ID = "E1ABCDEF123456"
REGION = "us-east-1"


def _make_distribution(*, enabled=True, comment="Test dist", price_class="PriceClass_100",
                       http_version="http2", ipv6=True, root_object="index.html",
                       viewer_protocol="redirect-to-https", compress=True,
                       aliases=None, web_acl_id=""):
    return {
        "Distribution": {
            "DistributionConfig": {
                "Enabled": enabled,
                "Comment": comment,
                "PriceClass": price_class,
                "HttpVersion": http_version,
                "IsIPV6Enabled": ipv6,
                "DefaultRootObject": root_object,
                "DefaultCacheBehavior": {
                    "ViewerProtocolPolicy": viewer_protocol,
                    "Compress": compress,
                },
                "Origins": {
                    "Items": [
                        {
                            "DomainName": "my-bucket.s3.amazonaws.com",
                            "Id": "S3-my-bucket",
                        }
                    ]
                },
                "Aliases": {"Items": aliases or ["cdn.example.com"]},
                "WebACLId": web_acl_id,
            }
        }
    }


@pytest.fixture()
def mock_cf_client():
    with patch("driftwatch.fetchers.cloudfront._get_cloudfront_client") as mock_factory:
        client = MagicMock()
        mock_factory.return_value = client
        yield client


def test_fetcher_registered():
    assert "cloudfront_distribution" in _FETCHER_REGISTRY


def test_fetch_returns_expected_fields(mock_cf_client):
    mock_cf_client.get_distribution.return_value = _make_distribution()
    result = fetch_cloudfront_distribution(DIST_ID, REGION)

    assert result.resource_id == DIST_ID
    assert result.resource_type == "cloudfront_distribution"
    assert result.config["enabled"] is True
    assert result.config["viewer_protocol_policy"] == "redirect-to-https"
    assert result.config["compress"] is True
    assert result.config["aliases"] == ["cdn.example.com"]


def test_origins_sorted_by_id(mock_cf_client):
    dist = _make_distribution()
    dist["Distribution"]["DistributionConfig"]["Origins"]["Items"] = [
        {"DomainName": "b.example.com", "Id": "origin-b"},
        {"DomainName": "a.example.com", "Id": "origin-a"},
    ]
    mock_cf_client.get_distribution.return_value = dist
    result = fetch_cloudfront_distribution(DIST_ID, REGION)
    ids = [o["origin_id"] for o in result.config["origins"]]
    assert ids == sorted(ids)


def test_not_found_returns_empty_config(mock_cf_client):
    from botocore.exceptions import ClientError
    mock_cf_client.get_distribution.side_effect = ClientError(
        {"Error": {"Code": "NoSuchDistribution", "Message": "Not found"}},
        "GetDistribution",
    )
    result = fetch_cloudfront_distribution(DIST_ID, REGION)
    assert result.config == {}


def test_aliases_sorted(mock_cf_client):
    dist = _make_distribution(aliases=["z.example.com", "a.example.com"])
    mock_cf_client.get_distribution.return_value = dist
    result = fetch_cloudfront_distribution(DIST_ID, REGION)
    assert result.config["aliases"] == ["a.example.com", "z.example.com"]

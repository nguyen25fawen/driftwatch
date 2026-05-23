"""Tests for the ELB fetcher."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from driftwatch.fetchers.elb import fetch_elb
from driftwatch.poller import _FETCHER_REGISTRY


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_lb(name: str = "my-alb") -> dict:
    return {
        "LoadBalancerArn": f"arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/{name}/abc123",
        "LoadBalancerName": name,
        "Type": "application",
        "Scheme": "internet-facing",
        "IpAddressType": "ipv4",
        "AvailabilityZones": [
            {"ZoneName": "us-east-1b"},
            {"ZoneName": "us-east-1a"},
        ],
    }


def _make_attributes(**overrides) -> list[dict]:
    defaults = {
        "deletion_protection.enabled": "false",
        "access_logs.s3.enabled": "false",
        "idle_timeout.timeout_seconds": "60",
    }
    defaults.update(overrides)
    return [{"Key": k, "Value": v} for k, v in defaults.items()]


@pytest.fixture()
def mock_elb_client():
    with patch("driftwatch.fetchers.elb._get_elb_client") as mock_factory:
        client = MagicMock()
        mock_factory.return_value = client
        yield client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_fetcher_registered():
    assert "elb" in _FETCHER_REGISTRY


def test_fetch_returns_expected_fields(mock_elb_client):
    lb = _make_lb()
    mock_elb_client.describe_load_balancers.return_value = {"LoadBalancers": [lb]}
    mock_elb_client.describe_load_balancer_attributes.return_value = {
        "Attributes": _make_attributes(**{"deletion_protection.enabled": "true"})
    }

    result = fetch_elb("my-alb", region="us-east-1")

    assert result.resource_id == "my-alb"
    assert result.resource_type == "elb"
    assert result.config["type"] == "application"
    assert result.config["scheme"] == "internet-facing"
    assert result.config["deletion_protection_enabled"] == "true"
    assert result.config["availability_zones"] == ["us-east-1a", "us-east-1b"]


def test_availability_zones_sorted(mock_elb_client):
    lb = _make_lb()
    lb["AvailabilityZones"] = [
        {"ZoneName": "us-east-1c"},
        {"ZoneName": "us-east-1a"},
        {"ZoneName": "us-east-1b"},
    ]
    mock_elb_client.describe_load_balancers.return_value = {"LoadBalancers": [lb]}
    mock_elb_client.describe_load_balancer_attributes.return_value = {
        "Attributes": _make_attributes()
    }

    result = fetch_elb("my-alb")
    assert result.config["availability_zones"] == ["us-east-1a", "us-east-1b", "us-east-1c"]


def test_not_found_returns_empty_config(mock_elb_client):
    mock_elb_client.exceptions.LoadBalancerNotFoundException = type(
        "LoadBalancerNotFoundException", (Exception,), {}
    )
    mock_elb_client.describe_load_balancers.side_effect = (
        mock_elb_client.exceptions.LoadBalancerNotFoundException("not found")
    )

    result = fetch_elb("missing-lb")
    assert result.config == {}


def test_empty_lb_list_returns_empty_config(mock_elb_client):
    mock_elb_client.describe_load_balancers.return_value = {"LoadBalancers": []}

    result = fetch_elb("ghost-lb")
    assert result.config == {}

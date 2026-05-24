"""Tests for the VPC fetcher."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.fetchers.vpc import fetch_vpc
from driftwatch.poller import _REGISTRY


def _make_vpc(**overrides) -> dict:
    base = {
        "VpcId": "vpc-abc123",
        "CidrBlock": "10.0.0.0/16",
        "State": "available",
        "IsDefault": False,
        "DhcpOptionsId": "dopt-111",
        "InstanceTenancy": "default",
        "Tags": [{"Key": "Name", "Value": "my-vpc"}],
        "Ipv6CidrBlockAssociationSet": [],
    }
    base.update(overrides)
    return base


@pytest.fixture()
def mock_vpc_client():
    with patch("driftwatch.fetchers.vpc._get_vpc_client") as mock_factory:
        client = MagicMock()
        mock_factory.return_value = client

        client.describe_vpcs.return_value = {"Vpcs": [_make_vpc()]}
        client.describe_flow_logs.return_value = {"FlowLogs": []}

        yield client


def test_fetcher_registered():
    assert "vpc" in _REGISTRY


def test_fetch_returns_expected_fields(mock_vpc_client):
    result = fetch_vpc("vpc-abc123")

    assert result.resource_id == "vpc-abc123"
    assert result.config["cidr_block"] == "10.0.0.0/16"
    assert result.config["state"] == "available"
    assert result.config["is_default"] is False
    assert result.config["instance_tenancy"] == "default"
    assert result.config["dhcp_options_id"] == "dopt-111"
    assert result.config["tags"] == {"Name": "my-vpc"}


def test_flow_logs_enabled_when_present(mock_vpc_client):
    mock_vpc_client.describe_flow_logs.return_value = {
        "FlowLogs": [{"FlowLogId": "fl-1", "ResourceId": "vpc-abc123"}]
    }
    result = fetch_vpc("vpc-abc123")
    assert result.config["flow_logs_enabled"] is True


def test_flow_logs_disabled_when_absent(mock_vpc_client):
    mock_vpc_client.describe_flow_logs.return_value = {"FlowLogs": []}
    result = fetch_vpc("vpc-abc123")
    assert result.config["flow_logs_enabled"] is False


def test_ipv6_cidr_blocks_sorted(mock_vpc_client):
    mock_vpc_client.describe_vpcs.return_value = {
        "Vpcs": [
            _make_vpc(
                Ipv6CidrBlockAssociationSet=[
                    {"Ipv6CidrBlock": "2600::/56"},
                    {"Ipv6CidrBlock": "2400::/56"},
                ]
            )
        ]
    }
    result = fetch_vpc("vpc-abc123")
    assert result.config["ipv6_cidr_blocks"] == ["2400::/56", "2600::/56"]


def test_vpc_not_found_returns_empty_config(mock_vpc_client):
    mock_vpc_client.describe_vpcs.return_value = {"Vpcs": []}
    result = fetch_vpc("vpc-missing")
    assert result.config == {}
    assert result.resource_id == "vpc-missing"

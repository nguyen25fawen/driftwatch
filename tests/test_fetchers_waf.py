"""Tests for the WAFv2 Web ACL fetcher."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.fetchers.waf import fetch_waf_web_acl
from driftwatch.poller import _FETCHER_REGISTRY


WACL_ID = "MyWebACL/aabbccdd-1234-5678-abcd-ef0123456789"


def _make_web_acl(
    name: str = "MyWebACL",
    wacl_id: str = "aabbccdd-1234-5678-abcd-ef0123456789",
    default_action: str = "Allow",
    rules: list | None = None,
    capacity: int = 150,
) -> dict:
    if rules is None:
        rules = [
            {"Name": "AWSManagedRulesCommonRuleSet", "Priority": 1, "OverrideAction": {"None": {}}},
            {"Name": "BlockBadBots", "Priority": 2, "Action": {"Block": {}}},
        ]
    return {
        "WebACL": {
            "Name": name,
            "Id": wacl_id,
            "DefaultAction": {default_action: {}},
            "ManagedByFirewallManager": False,
            "Rules": rules,
            "Capacity": capacity,
        },
        "LockToken": "lock-token",
    }


@pytest.fixture()
def mock_waf_client():
    with patch("driftwatch.fetchers.waf._get_waf_client") as mock_factory:
        client = MagicMock()
        mock_factory.return_value = client
        yield client


def test_fetcher_registered():
    assert "waf_web_acl" in _FETCHER_REGISTRY


def test_fetch_returns_expected_fields(mock_waf_client):
    mock_waf_client.get_web_acl.return_value = _make_web_acl()
    result = fetch_waf_web_acl(WACL_ID)

    assert result["name"] == "MyWebACL"
    assert result["id"] == "aabbccdd-1234-5678-abcd-ef0123456789"
    assert result["default_action"] == "allow"
    assert result["managed_by_firewall_manager"] is False
    assert result["rule_count"] == 2
    assert result["capacity"] == 150


def test_rules_sorted_by_priority(mock_waf_client):
    rules = [
        {"Name": "RuleB", "Priority": 10, "Action": {"Count": {}}},
        {"Name": "RuleA", "Priority": 1, "Action": {"Block": {}}},
    ]
    mock_waf_client.get_web_acl.return_value = _make_web_acl(rules=rules)
    result = fetch_waf_web_acl(WACL_ID)

    priorities = [r["priority"] for r in result["rules"]]
    assert priorities == sorted(priorities)


def test_not_found_returns_empty(mock_waf_client):
    from botocore.exceptions import ClientError

    mock_waf_client.get_web_acl.side_effect = ClientError(
        {"Error": {"Code": "WAFNonexistentItemException", "Message": "not found"}},
        "GetWebACL",
    )
    result = fetch_waf_web_acl(WACL_ID)
    assert result == {}


def test_region_passed_to_client():
    with patch("driftwatch.fetchers.waf._get_waf_client") as mock_factory:
        client = MagicMock()
        client.get_web_acl.return_value = _make_web_acl()
        mock_factory.return_value = client
        fetch_waf_web_acl(WACL_ID, region="eu-west-1")
        mock_factory.assert_called_once_with("eu-west-1")

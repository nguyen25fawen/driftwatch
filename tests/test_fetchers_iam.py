"""Tests for the IAM role fetcher."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.fetchers.iam import fetch_iam_role
from driftwatch.poller import _FETCHER_REGISTRY


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_role(name: str = "MyAppRole") -> dict:
    return {
        "RoleName": name,
        "Path": "/",
        "MaxSessionDuration": 3600,
        "AssumeRolePolicyDocument": {
            "Version": "2012-10-17",
            "Statement": [{"Effect": "Allow", "Principal": {"Service": "ec2.amazonaws.com"}, "Action": "sts:AssumeRole"}],
        },
        "Tags": [{"Key": "Environment", "Value": "production"}],
    }


@pytest.fixture()
def mock_iam_client():
    with patch("driftwatch.fetchers.iam._get_iam_client") as mock_factory:
        client = MagicMock()
        mock_factory.return_value = client

        client.get_role.return_value = {"Role": _make_role()}
        client.list_attached_role_policies.return_value = {
            "AttachedPolicies": [
                {"PolicyName": "CloudWatchLogsFullAccess"},
                {"PolicyName": "AmazonS3ReadOnlyAccess"},
            ]
        }
        client.list_role_policies.return_value = {"PolicyNames": []}

        yield client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_fetcher_registered():
    assert "iam_role" in _FETCHER_REGISTRY


def test_fetch_returns_expected_fields(mock_iam_client):
    result = fetch_iam_role("MyAppRole", "us-east-1")

    assert result["role_name"] == "MyAppRole"
    assert result["path"] == "/"
    assert result["max_session_duration"] == 3600
    assert result["assume_role_policy_statement_count"] == 1
    assert result["attached_policies"] == [
        "AmazonS3ReadOnlyAccess",
        "CloudWatchLogsFullAccess",
    ]
    assert result["inline_policies"] == []
    assert result["tags"] == {"Environment": "production"}


def test_attached_policies_sorted(mock_iam_client):
    result = fetch_iam_role("MyAppRole", "us-east-1")
    assert result["attached_policies"] == sorted(result["attached_policies"])


def test_inline_policies_returned(mock_iam_client):
    mock_iam_client.list_role_policies.return_value = {
        "PolicyNames": ["ZPolicy", "APolicy"]
    }
    result = fetch_iam_role("MyAppRole", "us-east-1")
    assert result["inline_policies"] == ["APolicy", "ZPolicy"]


def test_client_error_propagates(mock_iam_client):
    from botocore.exceptions import ClientError

    mock_iam_client.get_role.side_effect = ClientError(
        {"Error": {"Code": "NoSuchEntity", "Message": "Role not found"}},
        "GetRole",
    )
    with pytest.raises(ClientError):
        fetch_iam_role("NonExistentRole", "us-east-1")


def test_string_assume_role_doc_parsed(mock_iam_client):
    import json

    doc = json.dumps({
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow"}, {"Effect": "Deny"}],
    })
    role = _make_role()
    role["AssumeRolePolicyDocument"] = doc
    mock_iam_client.get_role.return_value = {"Role": role}

    result = fetch_iam_role("MyAppRole", "us-east-1")
    assert result["assume_role_policy_statement_count"] == 2

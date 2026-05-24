"""Tests for the CodeCommit repository fetcher."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.fetchers.codecommit import fetch_codecommit_repository
from driftwatch.poller import _FETCHER_REGISTRY


def _make_repo_meta(
    name: str = "my-repo",
    branch: str = "main",
    description: str = "A repo",
) -> dict:
    return {
        "repositoryMetadata": {
            "repositoryName": name,
            "defaultBranch": branch,
            "repositoryDescription": description,
        }
    }


def _make_rules_response(templates: list[str]) -> dict:
    return {"approvalRuleTemplateNames": templates}


@pytest.fixture()
def mock_cc_client():
    with patch("driftwatch.fetchers.codecommit._get_codecommit_client") as mock_factory:
        client = MagicMock()
        mock_factory.return_value = client
        yield client


def test_fetcher_registered():
    assert "codecommit_repository" in _FETCHER_REGISTRY


def test_fetch_returns_expected_fields(mock_cc_client):
    mock_cc_client.get_repository.return_value = _make_repo_meta(
        name="my-repo", branch="main", description="A repo"
    )
    mock_cc_client.list_associated_approval_rule_templates_for_repository.return_value = (
        _make_rules_response(["rule-b", "rule-a"])
    )

    result = fetch_codecommit_repository("my-repo")

    assert result["repository_name"] == "my-repo"
    assert result["default_branch"] == "main"
    assert result["repository_description"] == "A repo"
    assert result["approval_rule_templates"] == ["rule-a", "rule-b"]


def test_approval_rule_templates_sorted(mock_cc_client):
    mock_cc_client.get_repository.return_value = _make_repo_meta()
    mock_cc_client.list_associated_approval_rule_templates_for_repository.return_value = (
        _make_rules_response(["zzz-rule", "aaa-rule", "mmm-rule"])
    )

    result = fetch_codecommit_repository("my-repo")

    assert result["approval_rule_templates"] == ["aaa-rule", "mmm-rule", "zzz-rule"]


def test_repo_not_found_returns_empty(mock_cc_client):
    from botocore.exceptions import ClientError

    mock_cc_client.get_repository.side_effect = ClientError(
        {"Error": {"Code": "RepositoryDoesNotExistException", "Message": "Not found"}},
        "GetRepository",
    )

    result = fetch_codecommit_repository("missing-repo")

    assert result == {}


def test_approval_rules_error_returns_empty_list(mock_cc_client):
    from botocore.exceptions import ClientError

    mock_cc_client.get_repository.return_value = _make_repo_meta()
    mock_cc_client.list_associated_approval_rule_templates_for_repository.side_effect = (
        ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "Denied"}},
            "ListAssociatedApprovalRuleTemplatesForRepository",
        )
    )

    result = fetch_codecommit_repository("my-repo")

    assert result["approval_rule_templates"] == []
    assert result["repository_name"] == "my-repo"


def test_region_passed_to_client():
    with patch("driftwatch.fetchers.codecommit._get_codecommit_client") as mock_factory:
        client = MagicMock()
        client.get_repository.return_value = _make_repo_meta()
        client.list_associated_approval_rule_templates_for_repository.return_value = (
            _make_rules_response([])
        )
        mock_factory.return_value = client

        fetch_codecommit_repository("my-repo", region="eu-west-1")

        mock_factory.assert_called_once_with("eu-west-1")

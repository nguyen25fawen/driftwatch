"""Integration-style tests for CodeCommit fetcher against the example baseline."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from driftwatch.baseline import load_baselines
from driftwatch.detector import detect_drift
from driftwatch.fetchers.codecommit import fetch_codecommit_repository

BASELINE_PATH = (
    Path(__file__).parent.parent / "driftwatch" / "baselines" / "example_codecommit_baseline.json"
)


def _matching_response(expected: dict) -> dict:
    """Build a mock API response that matches the expected config."""
    return {
        "repositoryMetadata": {
            "repositoryName": expected["repository_name"],
            "defaultBranch": expected["default_branch"],
            "repositoryDescription": expected["repository_description"],
        }
    }


@pytest.fixture()
def mock_cc_client():
    with patch("driftwatch.fetchers.codecommit._get_codecommit_client") as mock_factory:
        client = MagicMock()
        mock_factory.return_value = client
        yield client


def test_example_baseline_loads():
    baselines = load_baselines(str(BASELINE_PATH))
    assert len(baselines) == 1
    assert baselines[0].resource_type == "codecommit_repository"


def test_no_drift_against_example_baseline(mock_cc_client):
    baselines = load_baselines(str(BASELINE_PATH))
    baseline = baselines[0]
    expected = baseline.expected_config

    mock_cc_client.get_repository.return_value = _matching_response(expected)
    mock_cc_client.list_associated_approval_rule_templates_for_repository.return_value = {
        "approvalRuleTemplateNames": expected["approval_rule_templates"]
    }

    actual = fetch_codecommit_repository(baseline.resource_id, region=baseline.region)
    result = detect_drift(baseline, actual)

    assert not result.drifted
    assert result.diffs == {}


def test_drift_detected_on_branch_change(mock_cc_client):
    baselines = load_baselines(str(BASELINE_PATH))
    baseline = baselines[0]
    expected = baseline.expected_config

    modified = dict(expected, default_branch="develop")
    mock_cc_client.get_repository.return_value = {
        "repositoryMetadata": {
            "repositoryName": modified["repository_name"],
            "defaultBranch": modified["default_branch"],
            "repositoryDescription": modified["repository_description"],
        }
    }
    mock_cc_client.list_associated_approval_rule_templates_for_repository.return_value = {
        "approvalRuleTemplateNames": modified["approval_rule_templates"]
    }

    actual = fetch_codecommit_repository(baseline.resource_id, region=baseline.region)
    result = detect_drift(baseline, actual)

    assert result.drifted
    assert "default_branch" in result.diffs
    assert result.diffs["default_branch"] == {"expected": "main", "actual": "develop"}

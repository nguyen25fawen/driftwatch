"""Tests for the ECR repository fetcher."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.fetchers.ecr import fetch_ecr_repository
from driftwatch.poller import _FETCHER_REGISTRY


def _make_repository(name: str = "my-repo") -> dict:
    return {
        "repositoryName": name,
        "repositoryArn": f"arn:aws:ecr:us-east-1:123456789012:repository/{name}",
        "imageTagMutability": "IMMUTABLE",
        "imageScanningConfiguration": {"scanOnPush": True},
        "encryptionConfiguration": {"encryptionType": "KMS"},
    }


@pytest.fixture
def mock_ecr_client():
    with patch("driftwatch.fetchers.ecr._get_ecr_client") as mock_factory:
        client = MagicMock()
        mock_factory.return_value = client

        # Default: no lifecycle policy
        not_found_exc = client.exceptions.LifecyclePolicyNotFoundException = type(
            "LifecyclePolicyNotFoundException", (Exception,), {}
        )
        client.get_lifecycle_policy.side_effect = not_found_exc()

        # Default: repo not found exception class
        client.exceptions.RepositoryNotFoundException = type(
            "RepositoryNotFoundException", (Exception,), {}
        )

        yield client


def test_fetcher_registered():
    assert "ecr_repository" in _FETCHER_REGISTRY


def test_fetch_returns_expected_fields(mock_ecr_client):
    repo = _make_repository("my-repo")
    mock_ecr_client.describe_repositories.return_value = {"repositories": [repo]}

    result = fetch_ecr_repository("my-repo")

    assert result.resource_id == "my-repo"
    assert result.resource_type == "ecr_repository"
    cfg = result.config
    assert cfg["image_tag_mutability"] == "IMMUTABLE"
    assert cfg["scan_on_push"] is True
    assert cfg["encryption_type"] == "KMS"
    assert cfg["lifecycle_policy_defined"] is False


def test_lifecycle_policy_detected(mock_ecr_client):
    repo = _make_repository("my-repo")
    mock_ecr_client.describe_repositories.return_value = {"repositories": [repo]}
    mock_ecr_client.get_lifecycle_policy.side_effect = None
    mock_ecr_client.get_lifecycle_policy.return_value = {
        "lifecyclePolicyText": '{"rules": []}'
    }

    result = fetch_ecr_repository("my-repo")

    assert result.config["lifecycle_policy_defined"] is True


def test_repo_not_found_returns_empty_config(mock_ecr_client):
    mock_ecr_client.describe_repositories.side_effect = (
        mock_ecr_client.exceptions.RepositoryNotFoundException()
    )

    result = fetch_ecr_repository("nonexistent-repo")

    assert result.config == {}
    assert result.resource_id == "nonexistent-repo"


def test_default_values_when_fields_absent(mock_ecr_client):
    repo = {
        "repositoryName": "bare-repo",
        "repositoryArn": "arn:aws:ecr:us-east-1:123456789012:repository/bare-repo",
    }
    mock_ecr_client.describe_repositories.return_value = {"repositories": [repo]}

    result = fetch_ecr_repository("bare-repo")

    cfg = result.config
    assert cfg["image_tag_mutability"] == "MUTABLE"
    assert cfg["scan_on_push"] is False
    assert cfg["encryption_type"] == "AES256"

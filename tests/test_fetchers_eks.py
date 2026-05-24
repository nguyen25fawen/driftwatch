"""Tests for the EKS cluster fetcher."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.fetchers.eks import fetch_eks_cluster
from driftwatch.poller import _FETCHER_REGISTRY


def _make_cluster(
    name: str = "my-cluster",
    version: str = "1.29",
    role_arn: str = "arn:aws:iam::123456789012:role/eks-role",
    public_access: bool = False,
    private_access: bool = True,
    logging_types: list[str] | None = None,
    encryption: bool = True,
    status: str = "ACTIVE",
) -> dict:
    if logging_types is None:
        logging_types = ["api", "audit"]
    return {
        "cluster": {
            "name": name,
            "version": version,
            "roleArn": role_arn,
            "resourcesVpcConfig": {
                "endpointPublicAccess": public_access,
                "endpointPrivateAccess": private_access,
            },
            "logging": {
                "clusterLogging": [
                    {"types": logging_types, "enabled": True}
                ]
            },
            "encryptionConfig": [{"provider": {"keyArn": "arn:aws:kms:us-east-1:123:key/abc"}}]
            if encryption
            else [],
            "status": status,
        }
    }


@pytest.fixture
def mock_eks_client():
    with patch("driftwatch.fetchers.eks._get_eks_client") as mock_factory:
        client = MagicMock()
        mock_factory.return_value = client
        yield client


def test_fetcher_registered():
    assert "eks_cluster" in _FETCHER_REGISTRY


def test_fetch_returns_expected_fields(mock_eks_client):
    mock_eks_client.describe_cluster.return_value = _make_cluster()
    result = fetch_eks_cluster("my-cluster")

    assert result.success is True
    assert result.resource_id == "my-cluster"
    cfg = result.config
    assert cfg["name"] == "my-cluster"
    assert cfg["version"] == "1.29"
    assert cfg["endpoint_public_access"] is False
    assert cfg["endpoint_private_access"] is True
    assert cfg["encryption_enabled"] is True
    assert cfg["status"] == "ACTIVE"


def test_logging_types_sorted(mock_eks_client):
    mock_eks_client.describe_cluster.return_value = _make_cluster(
        logging_types=["scheduler", "api", "audit"]
    )
    result = fetch_eks_cluster("my-cluster")
    assert result.config["logging_types"] == ["api", "audit", "scheduler"]


def test_cluster_not_found_returns_empty_config(mock_eks_client):
    not_found = mock_eks_client.exceptions.ResourceNotFoundException
    mock_eks_client.describe_cluster.side_effect = not_found()
    result = fetch_eks_cluster("missing-cluster")

    assert result.success is True
    assert result.config == {}


def test_no_logging_returns_empty_list(mock_eks_client):
    response = _make_cluster()
    response["cluster"]["logging"] = {"clusterLogging": [{"types": ["api"], "enabled": False}]}
    mock_eks_client.describe_cluster.return_value = response
    result = fetch_eks_cluster("my-cluster")
    assert result.config["logging_types"] == []


def test_region_passed_to_client():
    with patch("driftwatch.fetchers.eks._get_eks_client") as mock_factory:
        client = MagicMock()
        mock_factory.return_value = client
        client.describe_cluster.return_value = _make_cluster()
        fetch_eks_cluster("my-cluster", region="eu-west-1")
        mock_factory.assert_called_once_with("eu-west-1")

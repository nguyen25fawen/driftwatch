"""Tests for the CodePipeline fetcher."""
from __future__ import annotations

from unittest.mock import MagicMock, patch
from datetime import datetime

import pytest

from driftwatch.fetchers.codepipeline import fetch_codepipeline_pipeline
from driftwatch.poller import _REGISTRY


PIPELINE_NAME = "my-deploy-pipeline"


def _make_pipeline(name: str = PIPELINE_NAME, version: int = 1) -> dict:
    return {
        "pipeline": {
            "name": name,
            "roleArn": "arn:aws:iam::123456789012:role/CodePipelineServiceRole",
            "artifactStore": {
                "type": "S3",
                "location": "my-codepipeline-artifacts-bucket",
            },
            "stages": [
                {"name": "Source"},
                {"name": "Build"},
                {"name": "Deploy"},
            ],
            "version": version,
        },
        "metadata": {
            "created": datetime(2023, 1, 1),
            "updated": datetime(2023, 6, 1),
        },
    }


@pytest.fixture()
def mock_cp_client():
    with patch("driftwatch.fetchers.codepipeline._get_codepipeline_client") as mock_factory:
        client = MagicMock()
        mock_factory.return_value = client
        yield client


def test_fetcher_registered():
    assert "codepipeline" in _REGISTRY


def test_fetch_returns_expected_fields(mock_cp_client):
    mock_cp_client.get_pipeline.return_value = _make_pipeline()

    result = fetch_codepipeline_pipeline(PIPELINE_NAME)

    assert result.resource_id == PIPELINE_NAME
    assert result.resource_type == "codepipeline"
    cfg = result.config
    assert cfg["pipeline_name"] == PIPELINE_NAME
    assert cfg["artifact_store_type"] == "S3"
    assert cfg["artifact_store_location"] == "my-codepipeline-artifacts-bucket"
    assert cfg["stage_count"] == 3
    assert cfg["version"] == 1


def test_stage_names_sorted(mock_cp_client):
    mock_cp_client.get_pipeline.return_value = _make_pipeline()

    result = fetch_codepipeline_pipeline(PIPELINE_NAME)

    assert result.config["stage_names"] == ["Build", "Deploy", "Source"]


def test_pipeline_not_found_returns_empty_config(mock_cp_client):
    not_found = mock_cp_client.exceptions.PipelineNotFoundException = type(
        "PipelineNotFoundException", (Exception,), {}
    )
    mock_cp_client.get_pipeline.side_effect = not_found("not found")

    result = fetch_codepipeline_pipeline("nonexistent-pipeline")

    assert result.config == {}
    assert result.resource_id == "nonexistent-pipeline"


def test_region_forwarded_to_client():
    with patch("driftwatch.fetchers.codepipeline._get_codepipeline_client") as mock_factory:
        client = MagicMock()
        mock_factory.return_value = client
        client.get_pipeline.return_value = _make_pipeline()

        fetch_codepipeline_pipeline(PIPELINE_NAME, region="eu-west-1")

        mock_factory.assert_called_once_with("eu-west-1")

"""Tests for the Glue job fetcher."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from driftwatch.fetchers.glue import fetch_glue_job
from driftwatch.poller import _FETCHER_REGISTRY


def _make_job(
    name="my-etl-job",
    role="arn:aws:iam::123456789012:role/GlueServiceRole",
    glue_version="4.0",
    worker_type="G.1X",
    number_of_workers=5,
    max_retries=1,
    timeout=2880,
    script_location="s3://my-bucket/scripts/etl.py",
    python_version="3",
    connections=None,
    default_arguments=None,
    tags=None,
) -> dict:
    return {
        "Job": {
            "Name": name,
            "Role": role,
            "GlueVersion": glue_version,
            "WorkerType": worker_type,
            "NumberOfWorkers": number_of_workers,
            "MaxRetries": max_retries,
            "Timeout": timeout,
            "Command": {
                "ScriptLocation": script_location,
                "PythonVersion": python_version,
            },
            "Connections": {"Connections": connections or []},
            "DefaultArguments": default_arguments or {},
            "Tags": tags or {},
        }
    }


@pytest.fixture
def mock_glue_client():
    with patch("driftwatch.fetchers.glue._get_glue_client") as mock_factory:
        client = MagicMock()
        client.exceptions.EntityNotFoundException = Exception
        mock_factory.return_value = client
        yield client


def test_fetcher_registered():
    assert "glue_job" in _FETCHER_REGISTRY


def test_fetch_returns_expected_fields(mock_glue_client):
    mock_glue_client.get_job.return_value = _make_job()
    result = fetch_glue_job("my-etl-job", region="us-east-1")
    assert result.resource_id == "my-etl-job"
    assert result.config["glue_version"] == "4.0"
    assert result.config["worker_type"] == "G.1X"
    assert result.config["number_of_workers"] == 5
    assert result.config["script_location"] == "s3://my-bucket/scripts/etl.py"


def test_connections_sorted(mock_glue_client):
    mock_glue_client.get_job.return_value = _make_job(
        connections=["conn-b", "conn-a", "conn-c"]
    )
    result = fetch_glue_job("my-etl-job")
    assert result.config["connections"] == ["conn-a", "conn-b", "conn-c"]


def test_job_not_found_returns_empty_config(mock_glue_client):
    mock_glue_client.get_job.side_effect = Exception("EntityNotFoundException")
    result = fetch_glue_job("nonexistent-job")
    assert result.config == {}
    assert result.resource_id == "nonexistent-job"


def test_default_max_retries_zero(mock_glue_client):
    job_data = _make_job()
    del job_data["Job"]["MaxRetries"]
    mock_glue_client.get_job.return_value = job_data
    result = fetch_glue_job("my-etl-job")
    assert result.config["max_retries"] == 0

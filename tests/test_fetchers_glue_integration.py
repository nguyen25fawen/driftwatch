"""Integration tests: Glue fetcher against the example baseline."""
from __future__ import annotations

import json
import pathlib
import pytest
from unittest.mock import MagicMock, patch

from driftwatch.baseline import load_baselines
from driftwatch.detector import detect_drift
from driftwatch.fetchers.glue import fetch_glue_job

BASELINE_PATH = (
    pathlib.Path(__file__).parent.parent
    / "driftwatch"
    / "baselines"
    / "example_glue_baseline.json"
)


def _matching_response(baseline_cfg: dict) -> dict:
    """Build a mock get_job response that matches the baseline config."""
    return {
        "Job": {
            "Name": baseline_cfg["name"],
            "Role": baseline_cfg["role"],
            "GlueVersion": baseline_cfg["glue_version"],
            "WorkerType": baseline_cfg["worker_type"],
            "NumberOfWorkers": baseline_cfg["number_of_workers"],
            "MaxRetries": baseline_cfg["max_retries"],
            "Timeout": baseline_cfg["timeout"],
            "Command": {
                "ScriptLocation": baseline_cfg["script_location"],
                "PythonVersion": baseline_cfg["python_version"],
            },
            "Connections": {"Connections": baseline_cfg["connections"]},
            "DefaultArguments": baseline_cfg["default_arguments"],
            "Tags": baseline_cfg["tags"],
        }
    }


@pytest.fixture
def mock_glue_client():
    with patch("driftwatch.fetchers.glue._get_glue_client") as mock_factory:
        client = MagicMock()
        client.exceptions.EntityNotFoundException = Exception
        mock_factory.return_value = client
        yield client


def test_example_baseline_loads():
    baselines = load_baselines(str(BASELINE_PATH))
    assert len(baselines) == 1
    assert baselines[0].resource_type == "glue_job"


def test_no_drift_against_example_baseline(mock_glue_client):
    baselines = load_baselines(str(BASELINE_PATH))
    baseline = baselines[0]
    mock_glue_client.get_job.return_value = _matching_response(
        baseline.expected_config
    )
    poll = fetch_glue_job(baseline.resource_id, region=baseline.region)
    result = detect_drift(baseline, poll.config)
    assert not result.drifted


def test_drift_detected_on_worker_type_change(mock_glue_client):
    baselines = load_baselines(str(BASELINE_PATH))
    baseline = baselines[0]
    cfg = dict(baseline.expected_config)
    cfg["worker_type"] = "G.2X"
    mock_glue_client.get_job.return_value = _matching_response(cfg)
    poll = fetch_glue_job(baseline.resource_id, region=baseline.region)
    result = detect_drift(baseline, poll.config)
    assert result.drifted
    assert "worker_type" in result.drifted_keys


def test_drift_detected_on_missing_connection(mock_glue_client):
    baselines = load_baselines(str(BASELINE_PATH))
    baseline = baselines[0]
    cfg = dict(baseline.expected_config)
    cfg["connections"] = []
    mock_glue_client.get_job.return_value = _matching_response(cfg)
    poll = fetch_glue_job(baseline.resource_id, region=baseline.region)
    result = detect_drift(baseline, poll.config)
    assert result.drifted
    assert "connections" in result.drifted_keys

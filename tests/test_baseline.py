"""Tests for the baseline loader module."""

import json
import os
import tempfile

import pytest

from driftwatch.baseline import ResourceBaseline, load_baselines


SAMPLE_BASELINES = [
    {
        "resource_id": "sg-001",
        "resource_type": "aws_security_group",
        "region": "us-east-1",
        "expected_config": {"ingress_open_to_world": False},
    },
    {
        "resource_id": "bucket-test",
        "resource_type": "aws_s3_bucket",
        "expected_config": {"public_access_blocked": True},
    },
]


def _write_json(data: object) -> str:
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as fh:
        json.dump(data, fh)
    return path


def test_load_baselines_success():
    path = _write_json(SAMPLE_BASELINES)
    try:
        baselines = load_baselines(path)
        assert len(baselines) == 2
        assert baselines[0].resource_id == "sg-001"
        assert baselines[1].region == "us-east-1"  # default
    finally:
        os.unlink(path)


def test_load_baselines_missing_file():
    with pytest.raises(FileNotFoundError):
        load_baselines("/nonexistent/path/baseline.json")


def test_load_baselines_invalid_format():
    path = _write_json({"not": "a list"})
    try:
        with pytest.raises(ValueError, match="JSON array"):
            load_baselines(path)
    finally:
        os.unlink(path)


def test_resource_baseline_empty_id():
    with pytest.raises(ValueError, match="resource_id"):
        ResourceBaseline(resource_id="", resource_type="aws_s3_bucket", region="us-east-1")

"""Tests for the drift detection module."""

import pytest

from driftwatch.baseline import ResourceBaseline
from driftwatch.detector import DriftResult, detect_drift


@pytest.fixture()
def s3_baseline() -> ResourceBaseline:
    return ResourceBaseline(
        resource_id="bucket-prod",
        resource_type="aws_s3_bucket",
        region="us-east-1",
        expected_config={
            "versioning_enabled": True,
            "public_access_blocked": True,
            "logging_enabled": True,
        },
    )


def test_no_drift(s3_baseline: ResourceBaseline):
    live = {
        "versioning_enabled": True,
        "public_access_blocked": True,
        "logging_enabled": True,
        "extra_key": "ignored",
    }
    result = detect_drift(s3_baseline, live)
    assert not result.drifted
    assert result.differences == {}
    assert "[OK]" in result.summary()


def test_drift_detected(s3_baseline: ResourceBaseline):
    live = {
        "versioning_enabled": False,   # changed
        "public_access_blocked": True,
        "logging_enabled": True,
    }
    result = detect_drift(s3_baseline, live)
    assert result.drifted
    assert "versioning_enabled" in result.differences
    assert result.differences["versioning_enabled"] == {"expected": True, "actual": False}
    assert "[DRIFT]" in result.summary()


def test_missing_key_counts_as_drift(s3_baseline: ResourceBaseline):
    live: dict = {}  # all keys missing from live config
    result = detect_drift(s3_baseline, live)
    assert result.drifted
    assert len(result.differences) == 3


def test_drift_result_metadata(s3_baseline: ResourceBaseline):
    result = detect_drift(s3_baseline, {})
    assert result.resource_id == "bucket-prod"
    assert result.resource_type == "aws_s3_bucket"
    assert result.region == "us-east-1"

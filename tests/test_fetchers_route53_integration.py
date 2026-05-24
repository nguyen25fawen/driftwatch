"""Integration-style tests: load the example baseline and run drift detection."""
from __future__ import annotations

import json
import pathlib
from unittest.mock import MagicMock, patch

import pytest

from driftwatch.baseline import load_baselines
from driftwatch.detector import detect_drift
from driftwatch.fetchers.route53 import fetch_route53_hosted_zone

BASELINE_PATH = (
    pathlib.Path(__file__).parent.parent
    / "driftwatch"
    / "baselines"
    / "example_route53_baseline.json"
)
ZONE_ID = "Z1D633PJN98FT9"


def _matching_response() -> dict:
    return {
        "HostedZone": {
            "Id": f"/hostedzone/{ZONE_ID}",
            "Name": "example.com.",
            "Config": {"PrivateZone": False, "Comment": "Managed by DriftWatch"},
            "ResourceRecordSetCount": 5,
        },
        "VPCs": [],
    }


@pytest.fixture()
def mock_r53_client():
    with patch("driftwatch.fetchers.route53._get_route53_client") as mock_factory:
        client = MagicMock()
        mock_factory.return_value = client
        yield client


def test_example_baseline_loads():
    baselines = load_baselines(str(BASELINE_PATH))
    assert len(baselines) == 1
    assert baselines[0].resource_type == "route53_hosted_zone"


def test_no_drift_against_example_baseline(mock_r53_client):
    mock_r53_client.get_hosted_zone.return_value = _matching_response()
    baselines = load_baselines(str(BASELINE_PATH))
    bl = baselines[0]
    poll = fetch_route53_hosted_zone(bl.resource_id, bl.region)
    result = detect_drift(poll, bl)
    assert not result.has_drift


def test_drift_detected_on_record_count_change(mock_r53_client):
    resp = _matching_response()
    resp["HostedZone"]["ResourceRecordSetCount"] = 99
    mock_r53_client.get_hosted_zone.return_value = resp
    baselines = load_baselines(str(BASELINE_PATH))
    bl = baselines[0]
    poll = fetch_route53_hosted_zone(bl.resource_id, bl.region)
    result = detect_drift(poll, bl)
    assert result.has_drift
    assert "record_count" in result.drifted_keys


def test_drift_detected_on_private_zone_change(mock_r53_client):
    resp = _matching_response()
    resp["HostedZone"]["Config"]["PrivateZone"] = True
    mock_r53_client.get_hosted_zone.return_value = resp
    baselines = load_baselines(str(BASELINE_PATH))
    bl = baselines[0]
    poll = fetch_route53_hosted_zone(bl.resource_id, bl.region)
    result = detect_drift(poll, bl)
    assert result.has_drift
    assert "private_zone" in result.drifted_keys

"""Integration-style tests: load the example ELB baseline and run drift detection."""
from __future__ import annotations

import json
import pathlib
from unittest.mock import MagicMock, patch

import pytest

from driftwatch.baseline import load_baselines
from driftwatch.detector import detect_drift
from driftwatch.fetchers.elb import fetch_elb

BASELINE_PATH = (
    pathlib.Path(__file__).parent.parent
    / "driftwatch"
    / "baselines"
    / "example_elb_baseline.json"
)


def _matching_attrs() -> list[dict]:
    return [
        {"Key": "deletion_protection.enabled", "Value": "true"},
        {"Key": "access_logs.s3.enabled", "Value": "true"},
        {"Key": "idle_timeout.timeout_seconds", "Value": "60"},
    ]


@pytest.fixture()
def mock_elb_client():
    with patch("driftwatch.fetchers.elb._get_elb_client") as mock_factory:
        client = MagicMock()
        mock_factory.return_value = client
        yield client


def test_example_baseline_loads():
    baselines = load_baselines(str(BASELINE_PATH))
    assert len(baselines) == 1
    assert baselines[0].resource_type == "elb"
    assert baselines[0].resource_id == "my-application-lb"


def test_no_drift_against_example_baseline(mock_elb_client):
    baselines = load_baselines(str(BASELINE_PATH))
    baseline = baselines[0]

    mock_elb_client.describe_load_balancers.return_value = {
        "LoadBalancers": [
            {
                "LoadBalancerArn": "arn:aws:elasticloadbalancing:us-east-1:123:loadbalancer/app/my-application-lb/abc",
                "LoadBalancerName": "my-application-lb",
                "Type": "application",
                "Scheme": "internet-facing",
                "IpAddressType": "ipv4",
                "AvailabilityZones": [
                    {"ZoneName": "us-east-1c"},
                    {"ZoneName": "us-east-1a"},
                    {"ZoneName": "us-east-1b"},
                ],
            }
        ]
    }
    mock_elb_client.describe_load_balancer_attributes.return_value = {
        "Attributes": _matching_attrs()
    }

    poll = fetch_elb(baseline.resource_id, region=baseline.region)
    result = detect_drift(baseline, poll.config)
    assert not result.drifted


def test_drift_detected_on_scheme_change(mock_elb_client):
    baselines = load_baselines(str(BASELINE_PATH))
    baseline = baselines[0]

    mock_elb_client.describe_load_balancers.return_value = {
        "LoadBalancers": [
            {
                "LoadBalancerArn": "arn:aws:elasticloadbalancing:us-east-1:123:loadbalancer/app/my-application-lb/abc",
                "LoadBalancerName": "my-application-lb",
                "Type": "application",
                "Scheme": "internal",  # <-- drifted
                "IpAddressType": "ipv4",
                "AvailabilityZones": [
                    {"ZoneName": "us-east-1a"},
                    {"ZoneName": "us-east-1b"},
                    {"ZoneName": "us-east-1c"},
                ],
            }
        ]
    }
    mock_elb_client.describe_load_balancer_attributes.return_value = {
        "Attributes": _matching_attrs()
    }

    poll = fetch_elb(baseline.resource_id, region=baseline.region)
    result = detect_drift(baseline, poll.config)
    assert result.drifted
    assert "scheme" in result.diffs

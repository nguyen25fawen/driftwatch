"""Tests for driftwatch.scheduler."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.alerter import AlertConfig
from driftwatch.baseline import ResourceBaseline
from driftwatch.detector import DriftResult
from driftwatch.poller import PollResult
from driftwatch.scheduler import SchedulerConfig, run_cycle, start_scheduler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_baseline(resource_id: str = "bucket-1", resource_type: str = "s3") -> ResourceBaseline:
    return ResourceBaseline(
        resource_id=resource_id,
        resource_type=resource_type,
        expected_config={"versioning": "Enabled"},
    )


def _alert_cfg() -> AlertConfig:
    return AlertConfig(channels=["log"])


# ---------------------------------------------------------------------------
# SchedulerConfig
# ---------------------------------------------------------------------------

def test_scheduler_config_defaults() -> None:
    cfg = SchedulerConfig()
    assert cfg.interval_seconds == 300
    assert cfg.max_cycles is None


def test_scheduler_config_invalid_interval() -> None:
    with pytest.raises(ValueError, match="interval_seconds"):
        SchedulerConfig(interval_seconds=0)


# ---------------------------------------------------------------------------
# run_cycle
# ---------------------------------------------------------------------------

def test_run_cycle_no_drift() -> None:
    baseline = _make_baseline()
    poll_ok = PollResult(resource_id=baseline.resource_id, success=True, config={"versioning": "Enabled"})
    drift_none = DriftResult(resource_id=baseline.resource_id, resource_type="s3", drifted=False, diffs={})

    with patch("driftwatch.scheduler.poll_resource", return_value=poll_ok), \
         patch("driftwatch.scheduler.detect_drift", return_value=drift_none), \
         patch("driftwatch.scheduler.dispatch_alerts") as mock_dispatch:
        count = run_cycle([baseline], _alert_cfg())

    assert count == 0
    mock_dispatch.assert_called_once()


def test_run_cycle_drift_detected() -> None:
    baseline = _make_baseline()
    poll_ok = PollResult(resource_id=baseline.resource_id, success=True, config={"versioning": "Suspended"})
    drift_yes = DriftResult(
        resource_id=baseline.resource_id,
        resource_type="s3",
        drifted=True,
        diffs={"versioning": {"expected": "Enabled", "actual": "Suspended"}},
    )

    with patch("driftwatch.scheduler.poll_resource", return_value=poll_ok), \
         patch("driftwatch.scheduler.detect_drift", return_value=drift_yes), \
         patch("driftwatch.scheduler.dispatch_alerts"):
        count = run_cycle([baseline], _alert_cfg())

    assert count == 1


def test_run_cycle_poll_failure_skips_detect() -> None:
    baseline = _make_baseline()
    poll_fail = PollResult(resource_id=baseline.resource_id, success=False, error="timeout")

    with patch("driftwatch.scheduler.poll_resource", return_value=poll_fail), \
         patch("driftwatch.scheduler.detect_drift") as mock_detect, \
         patch("driftwatch.scheduler.dispatch_alerts"):
        count = run_cycle([baseline], _alert_cfg())

    mock_detect.assert_not_called()
    assert count == 0


# ---------------------------------------------------------------------------
# start_scheduler
# ---------------------------------------------------------------------------

def test_start_scheduler_runs_n_cycles() -> None:
    baseline = _make_baseline()
    poll_ok = PollResult(resource_id=baseline.resource_id, success=True, config={"versioning": "Enabled"})
    drift_none = DriftResult(resource_id=baseline.resource_id, resource_type="s3", drifted=False, diffs={})
    sleep_mock = MagicMock()

    with patch("driftwatch.scheduler.poll_resource", return_value=poll_ok), \
         patch("driftwatch.scheduler.detect_drift", return_value=drift_none), \
         patch("driftwatch.scheduler.dispatch_alerts"):
        cfg = SchedulerConfig(interval_seconds=1, max_cycles=3)
        start_scheduler([baseline], cfg, _sleep=sleep_mock)

    # sleep called between cycles, so max_cycles-1 times
    assert sleep_mock.call_count == 2

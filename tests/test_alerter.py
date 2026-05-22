"""Tests for the DriftWatch alerting module."""

from __future__ import annotations

from typing import List
from unittest.mock import patch

import pytest

from driftwatch.alerter import AlertConfig, _ALERT_HANDLERS, dispatch_alerts, register_handler
from driftwatch.detector import DriftResult


def _make_drift_result(drifted: bool = True) -> DriftResult:
    return DriftResult(
        resource_id="bucket-1",
        resource_type="s3",
        drifted=drifted,
        drifted_keys=["versioning"] if drifted else [],
        expected={"versioning": "Enabled"},
        actual={"versioning": "Suspended"},
    )


def test_alert_config_default_channels():
    config = AlertConfig()
    assert config.channels == ["log"]


def test_alert_config_empty_channels_raises():
    with pytest.raises(ValueError, match="at least one channel"):
        AlertConfig(channels=[])


def test_dispatch_alerts_no_drift_returns_empty():
    config = AlertConfig(channels=["log"])
    result = _make_drift_result(drifted=False)
    notified = dispatch_alerts(result, config)
    assert notified == []


def test_dispatch_alerts_calls_registered_handler():
    called_with: List[DriftResult] = []

    @register_handler("test_channel")
    def _handler(r: DriftResult) -> None:
        called_with.append(r)

    config = AlertConfig(channels=["test_channel"])
    result = _make_drift_result()
    notified = dispatch_alerts(result, config)

    assert "test_channel" in notified
    assert len(called_with) == 1
    assert called_with[0] is result


def test_dispatch_alerts_unknown_channel_skipped(caplog):
    config = AlertConfig(channels=["nonexistent_channel_xyz"])
    result = _make_drift_result()
    notified = dispatch_alerts(result, config)
    assert notified == []
    assert "nonexistent_channel_xyz" in caplog.text


def test_dispatch_alerts_handler_exception_does_not_propagate(caplog):
    @register_handler("broken_channel")
    def _broken(_r: DriftResult) -> None:
        raise RuntimeError("handler failure")

    config = AlertConfig(channels=["broken_channel"])
    result = _make_drift_result()
    notified = dispatch_alerts(result, config)
    assert notified == []
    assert "broken_channel" in caplog.text


def test_log_and_console_handlers_registered():
    # Importing built-in handlers should auto-register them
    import driftwatch.handlers.log_handler  # noqa: F401
    import driftwatch.handlers.console_handler  # noqa: F401

    assert "log" in _ALERT_HANDLERS
    assert "console" in _ALERT_HANDLERS

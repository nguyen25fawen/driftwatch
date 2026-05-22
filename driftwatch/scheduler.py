"""Scheduler for periodic drift-watch polling cycles."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from driftwatch.alerter import AlertConfig, dispatch_alerts
from driftwatch.baseline import ResourceBaseline
from driftwatch.detector import detect_drift
from driftwatch.poller import poll_resource

logger = logging.getLogger(__name__)


@dataclass
class SchedulerConfig:
    """Configuration for the drift-watch scheduler."""

    interval_seconds: int = 300
    alert_config: AlertConfig = field(default_factory=lambda: AlertConfig(channels=["log"]))
    max_cycles: Optional[int] = None  # None means run forever

    def __post_init__(self) -> None:
        if self.interval_seconds <= 0:
            raise ValueError("interval_seconds must be a positive integer")


def run_cycle(
    baselines: List[ResourceBaseline],
    alert_config: AlertConfig,
    *,
    _sleep: Callable[[float], None] = time.sleep,
) -> int:
    """Run a single polling cycle across all baselines.

    Returns the number of drifted resources detected.
    """
    drift_count = 0
    for baseline in baselines:
        logger.debug("Polling resource: %s (%s)", baseline.resource_id, baseline.resource_type)
        poll_result = poll_resource(baseline)
        if not poll_result.success:
            logger.warning(
                "Poll failed for %s: %s", baseline.resource_id, poll_result.error
            )
            continue

        drift_result = detect_drift(baseline, poll_result.config)
        if drift_result.drifted:
            drift_count += 1
            logger.info(
                "Drift detected for %s: %d field(s) changed",
                baseline.resource_id,
                len(drift_result.diffs),
            )

        dispatch_alerts([drift_result], alert_config)

    return drift_count


def start_scheduler(
    baselines: List[ResourceBaseline],
    config: SchedulerConfig,
    *,
    _sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Start the scheduler loop, blocking until max_cycles is reached."""
    cycle = 0
    logger.info(
        "Scheduler started — interval=%ds, resources=%d",
        config.interval_seconds,
        len(baselines),
    )
    while config.max_cycles is None or cycle < config.max_cycles:
        logger.info("Starting cycle %d", cycle + 1)
        drifted = run_cycle(baselines, config.alert_config, _sleep=_sleep)
        logger.info("Cycle %d complete — %d drift(s) found", cycle + 1, drifted)
        cycle += 1
        if config.max_cycles is None or cycle < config.max_cycles:
            _sleep(config.interval_seconds)

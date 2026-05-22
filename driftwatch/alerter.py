"""Alerting module for DriftWatch — dispatches drift alerts to configured channels."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Dict, List

from driftwatch.detector import DriftResult

logger = logging.getLogger(__name__)

# Registry of alert handlers keyed by channel name
_ALERT_HANDLERS: Dict[str, Callable[[DriftResult], None]] = {}


def register_handler(channel: str) -> Callable:
    """Decorator to register an alert handler for a named channel."""

    def decorator(fn: Callable[[DriftResult], None]) -> Callable:
        _ALERT_HANDLERS[channel] = fn
        logger.debug("Registered alert handler for channel '%s'", channel)
        return fn

    return decorator


@dataclass
class AlertConfig:
    """Configuration for which channels to dispatch alerts to."""

    channels: List[str] = field(default_factory=lambda: ["log"])

    def __post_init__(self) -> None:
        if not self.channels:
            raise ValueError("AlertConfig must specify at least one channel.")


def dispatch_alerts(result: DriftResult, config: AlertConfig) -> List[str]:
    """Dispatch a DriftResult to all configured channels.

    Returns a list of channels that were successfully notified.
    """
    if not result.drifted:
        return []

    notified: List[str] = []
    for channel in config.channels:
        handler = _ALERT_HANDLERS.get(channel)
        if handler is None:
            logger.warning("No handler registered for alert channel '%s'", channel)
            continue
        try:
            handler(result)
            notified.append(channel)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Alert handler '%s' raised an error: %s", channel, exc)

    return notified

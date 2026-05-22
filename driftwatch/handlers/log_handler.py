"""Log-based alert handler — writes drift alerts to the Python logging system."""

from __future__ import annotations

import logging

from driftwatch.alerter import register_handler
from driftwatch.detector import DriftResult

logger = logging.getLogger(__name__)


@register_handler("log")
def handle_log(result: DriftResult) -> None:
    """Log a drift alert using the standard logging framework."""
    logger.warning(
        "[DRIFT ALERT] resource_id=%s type=%s drifted_keys=%s",
        result.resource_id,
        result.resource_type,
        ", ".join(result.drifted_keys),
    )
    for key in result.drifted_keys:
        expected = result.expected.get(key, "<missing>")
        actual = result.actual.get(key, "<missing>")
        logger.warning(
            "  key='%s'  expected=%r  actual=%r",
            key,
            expected,
            actual,
        )

"""Cloud resource config poller for DriftWatch."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Registry of provider fetch functions keyed by resource_type
_FETCHERS: Dict[str, Callable[[str], Dict[str, Any]]] = {}


def register_fetcher(resource_type: str) -> Callable:
    """Decorator to register a fetcher function for a resource type."""

    def decorator(fn: Callable[[str], Dict[str, Any]]) -> Callable:
        _FETCHERS[resource_type] = fn
        logger.debug("Registered fetcher for resource_type=%s", resource_type)
        return fn

    return decorator


@dataclass
class PollResult:
    """Holds the live config fetched for a single resource."""

    resource_id: str
    resource_type: str
    config: Dict[str, Any]
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None


def poll_resource(resource_id: str, resource_type: str) -> PollResult:
    """Fetch the live config for *one* resource.

    Args:
        resource_id: Cloud resource identifier (e.g. bucket name, instance id).
        resource_type: Type string that maps to a registered fetcher.

    Returns:
        A :class:`PollResult` with the fetched config or an error message.
    """
    fetcher = _FETCHERS.get(resource_type)
    if fetcher is None:
        msg = f"No fetcher registered for resource_type='{resource_type}'"
        logger.warning(msg)
        return PollResult(resource_id=resource_id, resource_type=resource_type, config={}, error=msg)

    try:
        config = fetcher(resource_id)
        logger.info("Polled %s / %s successfully", resource_type, resource_id)
        return PollResult(resource_id=resource_id, resource_type=resource_type, config=config)
    except Exception as exc:  # noqa: BLE001
        msg = f"Fetcher raised an exception: {exc}"
        logger.error("Error polling %s / %s: %s", resource_type, resource_id, exc)
        return PollResult(resource_id=resource_id, resource_type=resource_type, config={}, error=msg)


def poll_all(baselines: List[Any]) -> List[PollResult]:
    """Poll every resource described in *baselines*.

    Args:
        baselines: List of :class:`~driftwatch.baseline.ResourceBaseline` objects.

    Returns:
        A list of :class:`PollResult` objects, one per baseline entry.
    """
    results: List[PollResult] = []
    for bl in baselines:
        result = poll_resource(bl.resource_id, bl.resource_type)
        results.append(result)
    return results

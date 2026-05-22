"""Drift detection logic: compares live config against baselines."""

from dataclasses import dataclass, field
from typing import Any

from driftwatch.baseline import ResourceBaseline


@dataclass
class DriftResult:
    """Captures the drift findings for a single resource."""

    resource_id: str
    resource_type: str
    region: str
    drifted: bool
    differences: dict[str, dict[str, Any]] = field(default_factory=dict)

    def summary(self) -> str:
        if not self.drifted:
            return f"[OK] {self.resource_id} — no drift detected"
        keys = ", ".join(self.differences.keys())
        return f"[DRIFT] {self.resource_id} — fields changed: {keys}"


def detect_drift(
    baseline: ResourceBaseline,
    live_config: dict[str, Any],
) -> DriftResult:
    """Compare a live resource config against its baseline.

    Only keys present in the baseline are checked; extra keys in the
    live config are ignored.

    Args:
        baseline: The expected configuration for the resource.
        live_config: The current configuration fetched from the cloud provider.

    Returns:
        A DriftResult describing any differences found.
    """
    differences: dict[str, dict[str, Any]] = {}

    for key, expected_value in baseline.expected_config.items():
        live_value = live_config.get(key)
        if live_value != expected_value:
            differences[key] = {"expected": expected_value, "actual": live_value}

    return DriftResult(
        resource_id=baseline.resource_id,
        resource_type=baseline.resource_type,
        region=baseline.region,
        drifted=bool(differences),
        differences=differences,
    )

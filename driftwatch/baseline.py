"""Baseline configuration loader and schema definitions."""

import json
import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResourceBaseline:
    """Represents the expected (baseline) configuration for a cloud resource."""

    resource_id: str
    resource_type: str
    region: str
    expected_config: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.resource_id:
            raise ValueError("resource_id must not be empty")
        if not self.resource_type:
            raise ValueError("resource_type must not be empty")


def load_baselines(path: str) -> list[ResourceBaseline]:
    """Load resource baselines from a JSON file.

    Args:
        path: Path to the baseline JSON file.

    Returns:
        A list of ResourceBaseline objects.

    Raises:
        FileNotFoundError: If the baseline file does not exist.
        ValueError: If the file contains invalid data.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Baseline file not found: {path}")

    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)

    if not isinstance(raw, list):
        raise ValueError("Baseline file must contain a JSON array of resource definitions")

    baselines: list[ResourceBaseline] = []
    for entry in raw:
        baselines.append(
            ResourceBaseline(
                resource_id=entry["resource_id"],
                resource_type=entry["resource_type"],
                region=entry.get("region", "us-east-1"),
                expected_config=entry.get("expected_config", {}),
            )
        )
    return baselines

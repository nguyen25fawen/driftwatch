"""Console alert handler — prints drift alerts to stdout in a human-readable format."""

from __future__ import annotations

from driftwatch.alerter import register_handler
from driftwatch.detector import DriftResult

_SEPARATOR = "-" * 60


@register_handler("console")
def handle_console(result: DriftResult) -> None:
    """Print a formatted drift alert to stdout."""
    print(_SEPARATOR)
    print(f"DRIFT DETECTED")
    print(f"  Resource ID  : {result.resource_id}")
    print(f"  Resource Type: {result.resource_type}")
    print(f"  Drifted Keys : {', '.join(result.drifted_keys)}")
    print()
    print(f"  {'Key':<30} {'Expected':<20} {'Actual':<20}")
    print(f"  {'---':<30} {'--------':<20} {'------':<20}")
    for key in result.drifted_keys:
        expected = result.expected.get(key, "<missing>")
        actual = result.actual.get(key, "<missing>")
        print(f"  {key:<30} {str(expected):<20} {str(actual):<20}")
    print(_SEPARATOR)

"""Fetcher for AWS CloudWatch Alarm configurations."""

from __future__ import annotations

import boto3
from typing import Any

from driftwatch.poller import register_fetcher, PollResult


def _get_cloudwatch_client(region: str | None = None) -> Any:
    kwargs = {"region_name": region} if region else {}
    return boto3.client("cloudwatch", **kwargs)


@register_fetcher("cloudwatch_alarm")
def fetch_cloudwatch_alarm(resource_id: str, region: str | None = None) -> PollResult:
    """Fetch configuration for a CloudWatch Alarm by name.

    Args:
        resource_id: The alarm name.
        region: Optional AWS region override.

    Returns:
        PollResult with alarm config or error details.
    """
    client = _get_cloudwatch_client(region)
    try:
        response = client.describe_alarms(AlarmNames=[resource_id], MaxRecords=1)
    except Exception as exc:  # noqa: BLE001
        return PollResult.ok(resource_id, {}, error=str(exc))

    alarms = response.get("MetricAlarms", [])
    if not alarms:
        return PollResult.ok(
            resource_id,
            {},
            error=f"CloudWatch alarm '{resource_id}' not found",
        )

    alarm = alarms[0]
    config: dict[str, Any] = {
        "alarm_name": alarm.get("AlarmName"),
        "alarm_description": alarm.get("AlarmDescription", ""),
        "metric_name": alarm.get("MetricName"),
        "namespace": alarm.get("Namespace"),
        "statistic": alarm.get("Statistic"),
        "comparison_operator": alarm.get("ComparisonOperator"),
        "threshold": alarm.get("Threshold"),
        "evaluation_periods": alarm.get("EvaluationPeriods"),
        "period": alarm.get("Period"),
        "treat_missing_data": alarm.get("TreatMissingData", "missing"),
        "actions_enabled": alarm.get("ActionsEnabled", True),
        "alarm_actions": sorted(alarm.get("AlarmActions", [])),
        "ok_actions": sorted(alarm.get("OKActions", [])),
        "insufficient_data_actions": sorted(
            alarm.get("InsufficientDataActions", [])
        ),
    }
    return PollResult.ok(resource_id, config)

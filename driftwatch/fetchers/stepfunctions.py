"""Fetcher for AWS Step Functions state machines."""
from __future__ import annotations

import boto3
from typing import Any

from driftwatch.poller import register_fetcher, PollResult


def _get_sfn_client(region: str | None = None):
    kwargs = {"region_name": region} if region else {}
    return boto3.client("stepfunctions", **kwargs)


@register_fetcher("stepfunctions")
def fetch_stepfunctions_statemachine(
    resource_id: str,
    region: str | None = None,
    **_: Any,
) -> PollResult:
    """Fetch configuration for a Step Functions state machine by ARN."""
    client = _get_sfn_client(region)

    try:
        resp = client.describe_state_machine(stateMachineArn=resource_id)
    except client.exceptions.StateMachineDoesNotExist:
        return PollResult.ok(resource_id=resource_id, config={})

    config: dict[str, Any] = {
        "name": resp.get("name"),
        "type": resp.get("type"),
        "status": resp.get("status"),
        "role_arn": resp.get("roleArn"),
        "logging_level": (
            resp.get("loggingConfiguration", {}).get("level", "OFF")
        ),
        "tracing_enabled": (
            resp.get("tracingConfiguration", {}).get("enabled", False)
        ),
    }

    return PollResult.ok(resource_id=resource_id, config=config)

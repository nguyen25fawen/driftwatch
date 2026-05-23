"""Fetcher for AWS ECS (Elastic Container Service) task definitions."""

from __future__ import annotations

import boto3
from typing import Any

from driftwatch.poller import register_fetcher, PollResult


def _get_ecs_client(region: str | None = None) -> Any:
    kwargs = {"region_name": region} if region else {}
    return boto3.client("ecs", **kwargs)


@register_fetcher("ecs_task_definition")
def fetch_ecs_task_definition(resource_id: str, region: str | None = None) -> PollResult:
    """Fetch the latest active revision of an ECS task definition.

    Args:
        resource_id: The task definition family name (e.g. ``my-service``).
        region: Optional AWS region override.

    Returns:
        A :class:`~driftwatch.poller.PollResult` containing selected fields
        from the task definition.
    """
    client = _get_ecs_client(region)
    try:
        response = client.describe_task_definition(
            taskDefinition=resource_id,
            include=["TAGS"],
        )
    except client.exceptions.ClientException as exc:
        return PollResult.error(resource_id, "ecs_task_definition", str(exc))

    td = response["taskDefinition"]

    containers = [
        {
            "name": c["name"],
            "image": c["image"],
            "cpu": c.get("cpu", 0),
            "memory": c.get("memory", 0),
            "essential": c.get("essential", True),
        }
        for c in td.get("containerDefinitions", [])
    ]
    containers.sort(key=lambda c: c["name"])

    config: dict[str, Any] = {
        "family": td["family"],
        "network_mode": td.get("networkMode", "bridge"),
        "cpu": td.get("cpu", ""),
        "memory": td.get("memory", ""),
        "requires_compatibilities": sorted(td.get("requiresCompatibilities", [])),
        "task_role_arn": td.get("taskRoleArn", ""),
        "execution_role_arn": td.get("executionRoleArn", ""),
        "containers": containers,
    }

    return PollResult.ok(resource_id, "ecs_task_definition", config)

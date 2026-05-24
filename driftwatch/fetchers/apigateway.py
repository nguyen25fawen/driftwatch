"""Fetcher for AWS API Gateway REST APIs."""
from __future__ import annotations

import boto3
from typing import Any

from driftwatch.poller import register_fetcher, PollResult


def _get_apigw_client(region: str | None = None):
    kwargs = {"region_name": region} if region else {}
    return boto3.client("apigateway", **kwargs)


@register_fetcher("apigateway_rest_api")
def fetch_apigateway_rest_api(resource_id: str, region: str | None = None) -> PollResult:
    """Fetch configuration for an API Gateway REST API.

    Args:
        resource_id: The REST API ID (e.g. ``abc123xyz```).
        region: Optional AWS region override.

    Returns:
        A :class:`~driftwatch.poller.PollResult` with the normalised config.
    """
    client = _get_apigw_client(region)

    try:
        api = client.get_rest_api(restApiId=resource_id)
    except client.exceptions.NotFoundException:
        return PollResult.ok(resource_id=resource_id, resource_type="apigateway_rest_api", config={})

    stages_resp = client.get_stages(restApiId=resource_id)
    stage_names: list[str] = sorted(
        s["stageName"] for s in stages_resp.get("item", [])
    )

    endpoint_types: list[str] = sorted(
        api.get("endpointConfiguration", {}).get("types", [])
    )

    config: dict[str, Any] = {
        "name": api.get("name"),
        "description": api.get("description", ""),
        "api_key_source": api.get("apiKeySource", "HEADER"),
        "endpoint_types": endpoint_types,
        "stages": stage_names,
        "minimum_compression_size": api.get("minimumCompressionSize"),
        "disable_execute_api_endpoint": api.get("disableExecuteApiEndpoint", False),
    }

    return PollResult.ok(
        resource_id=resource_id,
        resource_type="apigateway_rest_api",
        config=config,
    )

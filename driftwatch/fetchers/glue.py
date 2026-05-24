"""Fetcher for AWS Glue jobs."""
from __future__ import annotations

import boto3
from typing import Any

from driftwatch.poller import register_fetcher, PollResult


def _get_glue_client(region: str | None = None) -> Any:
    kwargs = {"region_name": region} if region else {}
    return boto3.client("glue", **kwargs)


@register_fetcher("glue_job")
def fetch_glue_job(resource_id: str, region: str | None = None) -> PollResult:
    """Fetch configuration for a Glue job by name."""
    client = _get_glue_client(region)
    try:
        response = client.get_job(JobName=resource_id)
    except client.exceptions.EntityNotFoundException:
        return PollResult.ok(resource_id=resource_id, config={})

    job = response.get("Job", {})
    command = job.get("Command", {})

    config: dict[str, Any] = {
        "name": job.get("Name"),
        "role": job.get("Role"),
        "glue_version": job.get("GlueVersion"),
        "worker_type": job.get("WorkerType"),
        "number_of_workers": job.get("NumberOfWorkers"),
        "max_retries": job.get("MaxRetries", 0),
        "timeout": job.get("Timeout"),
        "script_location": command.get("ScriptLocation"),
        "python_version": command.get("PythonVersion"),
        "connections": sorted(job.get("Connections", {}).get("Connections", [])),
        "default_arguments": job.get("DefaultArguments", {}),
        "tags": job.get("Tags", {}),
    }
    return PollResult.ok(resource_id=resource_id, config=config)

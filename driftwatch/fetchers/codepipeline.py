"""Fetcher for AWS CodePipeline pipeline configuration."""
from __future__ import annotations

import boto3
from typing import Any

from driftwatch.poller import register_fetcher, PollResult


def _get_codepipeline_client(region: str | None = None):
    kwargs = {"region_name": region} if region else {}
    return boto3.client("codepipeline", **kwargs)


@register_fetcher("codepipeline")
def fetch_codepipeline_pipeline(
    resource_id: str,
    region: str | None = None,
    **_: Any,
) -> PollResult:
    """Fetch configuration for a CodePipeline pipeline.

    Args:
        resource_id: The name of the pipeline.
        region: AWS region override.

    Returns:
        PollResult with the normalised pipeline config.
    """
    client = _get_codepipeline_client(region)

    try:
        resp = client.get_pipeline(name=resource_id)
    except client.exceptions.PipelineNotFoundException:
        return PollResult.ok(resource_id=resource_id, resource_type="codepipeline", config={})

    pipeline = resp.get("pipeline", {})
    metadata = resp.get("metadata", {})

    stages = pipeline.get("stages", [])
    stage_names = sorted(s.get("name", "") for s in stages)

    artifact_store = pipeline.get("artifactStore") or pipeline.get("artifactStores", {})
    artifact_type = ""
    artifact_location = ""
    if isinstance(artifact_store, dict):
        artifact_type = artifact_store.get("type", "")
        artifact_location = artifact_store.get("location", "")

    config: dict[str, Any] = {
        "pipeline_name": pipeline.get("name", resource_id),
        "role_arn": pipeline.get("roleArn", ""),
        "artifact_store_type": artifact_type,
        "artifact_store_location": artifact_location,
        "stage_count": len(stages),
        "stage_names": stage_names,
        "version": pipeline.get("version", 1),
        "created": str(metadata.get("created", "")),
        "updated": str(metadata.get("updated", "")),
    }

    return PollResult.ok(
        resource_id=resource_id,
        resource_type="codepipeline",
        config=config,
    )

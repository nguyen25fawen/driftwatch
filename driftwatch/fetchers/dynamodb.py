"""Fetcher for AWS DynamoDB table configuration."""

from __future__ import annotations

from typing import Any, Dict

import boto3

from driftwatch.poller import register_fetcher


def _get_dynamodb_client(region: str):
    return boto3.client("dynamodb", region_name=region)


@register_fetcher("dynamodb_table")
def fetch_dynamodb_table(resource_id: str, region: str, **_kwargs) -> Dict[str, Any]:
    """Fetch key configuration fields for a DynamoDB table.

    Args:
        resource_id: The DynamoDB table name.
        region: AWS region where the table resides.

    Returns:
        A flat dict of normalised table attributes suitable for drift comparison.
    """
    client = _get_dynamodb_client(region)
    resp = client.describe_table(TableName=resource_id)
    table = resp["Table"]

    billing_mode = table.get("BillingModeSummary", {}).get(
        "BillingMode", "PROVISIONED"
    )

    throughput = table.get("ProvisionedThroughput", {})

    sse = table.get("SSEDescription", {})
    sse_status = sse.get("Status", "DISABLED")

    stream_spec = table.get("StreamSpecification", {})
    streams_enabled = stream_spec.get("StreamEnabled", False)
    stream_view_type = stream_spec.get("StreamViewType", None)

    key_schema = sorted(
        [{"AttributeName": k["AttributeName"], "KeyType": k["KeyType"]} for k in table.get("KeySchema", [])],
        key=lambda x: x["KeyType"],
    )

    return {
        "table_name": table["TableName"],
        "table_status": table.get("TableStatus"),
        "billing_mode": billing_mode,
        "read_capacity_units": throughput.get("ReadCapacityUnits", 0),
        "write_capacity_units": throughput.get("WriteCapacityUnits", 0),
        "sse_status": sse_status,
        "streams_enabled": streams_enabled,
        "stream_view_type": stream_view_type,
        "key_schema": key_schema,
        "item_count": table.get("ItemCount", 0),
    }

"""Tests for the ECS task definition fetcher."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.fetchers.ecs import fetch_ecs_task_definition
from driftwatch.poller import _REGISTRY


def _make_task_definition(**overrides):
    base = {
        "family": "my-service",
        "networkMode": "awsvpc",
        "cpu": "256",
        "memory": "512",
        "requiresCompatibilities": ["FARGATE"],
        "taskRoleArn": "arn:aws:iam::123456789012:role/task-role",
        "executionRoleArn": "arn:aws:iam::123456789012:role/exec-role",
        "containerDefinitions": [
            {
                "name": "app",
                "image": "nginx:latest",
                "cpu": 128,
                "memory": 256,
                "essential": True,
            }
        ],
    }
    base.update(overrides)
    return base


def _make_describe_response(td: dict):
    return {"taskDefinition": td, "tags": []}


@pytest.fixture()
def mock_ecs_client():
    with patch("driftwatch.fetchers.ecs._get_ecs_client") as mock_factory:
        client = MagicMock()
        mock_factory.return_value = client
        yield client


def test_fetcher_registered():
    assert "ecs_task_definition" in _REGISTRY


def test_fetch_returns_expected_fields(mock_ecs_client):
    td = _make_task_definition()
    mock_ecs_client.describe_task_definition.return_value = _make_describe_response(td)

    result = fetch_ecs_task_definition("my-service")

    assert result.success
    assert result.config["family"] == "my-service"
    assert result.config["network_mode"] == "awsvpc"
    assert result.config["cpu"] == "256"
    assert result.config["memory"] == "512"
    assert result.config["requires_compatibilities"] == ["FARGATE"]
    assert result.config["task_role_arn"] == "arn:aws:iam::123456789012:role/task-role"
    assert result.config["execution_role_arn"] == "arn:aws:iam::123456789012:role/exec-role"


def test_containers_sorted_by_name(mock_ecs_client):
    td = _make_task_definition(
        containerDefinitions=[
            {"name": "sidecar", "image": "envoy:v1", "cpu": 64, "memory": 128, "essential": False},
            {"name": "app", "image": "nginx:latest", "cpu": 128, "memory": 256, "essential": True},
        ]
    )
    mock_ecs_client.describe_task_definition.return_value = _make_describe_response(td)

    result = fetch_ecs_task_definition("my-service")

    names = [c["name"] for c in result.config["containers"]]
    assert names == sorted(names)


def test_fetch_error_returns_failure(mock_ecs_client):
    mock_ecs_client.exceptions.ClientException = Exception
    mock_ecs_client.describe_task_definition.side_effect = Exception("not found")

    result = fetch_ecs_task_definition("missing-service")

    assert not result.success
    assert "not found" in result.error


def test_missing_optional_fields_use_defaults(mock_ecs_client):
    td = {
        "family": "bare-service",
        "containerDefinitions": [],
    }
    mock_ecs_client.describe_task_definition.return_value = _make_describe_response(td)

    result = fetch_ecs_task_definition("bare-service")

    assert result.config["network_mode"] == "bridge"
    assert result.config["cpu"] == ""
    assert result.config["task_role_arn"] == ""
    assert result.config["containers"] == []

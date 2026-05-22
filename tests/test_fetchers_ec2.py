"""Tests for driftwatch/fetchers/ec2.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import BotoCoreError, ClientError

from driftwatch.fetchers.ec2 import fetch_ec2_instance
from driftwatch.poller import _FETCHER_REGISTRY  # noqa: WPS450


_INSTANCE_ID = "i-0abc123def456789"


def _make_instance(**overrides):
    base = {
        "InstanceId": _INSTANCE_ID,
        "InstanceType": "t3.micro",
        "State": {"Name": "running"},
        "ImageId": "ami-12345678",
        "KeyName": "my-key",
        "Monitoring": {"State": "disabled"},
        "EbsOptimized": False,
        "VpcId": "vpc-aabbccdd",
        "SubnetId": "subnet-11223344",
        "SecurityGroups": [{"GroupId": "sg-aabbcc", "GroupName": "default"}],
        "IamInstanceProfile": {"Arn": "arn:aws:iam::123456789012:instance-profile/MyProfile"},
        "Tags": [{"Key": "Env", "Value": "prod"}],
    }
    base.update(overrides)
    return base


def _make_describe_response(instance):
    return {"Reservations": [{"Instances": [instance]}]}


@pytest.fixture()
def mock_ec2_client():
    with patch("driftwatch.fetchers.ec2._get_ec2_client") as mock_factory:
        client = MagicMock()
        mock_factory.return_value = client
        yield client


def test_fetcher_registered():
    assert "ec2_instance" in _FETCHER_REGISTRY


def test_fetch_returns_expected_fields(mock_ec2_client):
    mock_ec2_client.describe_instances.return_value = _make_describe_response(
        _make_instance()
    )
    result = fetch_ec2_instance(_INSTANCE_ID)

    assert result["instance_type"] == "t3.micro"
    assert result["state"] == "running"
    assert result["image_id"] == "ami-12345678"
    assert result["monitoring_enabled"] is False
    assert result["security_group_ids"] == ["sg-aabbcc"]
    assert result["tags"] == {"Env": "prod"}


def test_fetch_monitoring_enabled(mock_ec2_client):
    mock_ec2_client.describe_instances.return_value = _make_describe_response(
        _make_instance(Monitoring={"State": "enabled"})
    )
    result = fetch_ec2_instance(_INSTANCE_ID)
    assert result["monitoring_enabled"] is True


def test_fetch_instance_not_found_raises_value_error(mock_ec2_client):
    error_response = {"Error": {"Code": "InvalidInstanceID.NotFound", "Message": "Not found"}}
    mock_ec2_client.describe_instances.side_effect = ClientError(error_response, "DescribeInstances")

    with pytest.raises(ValueError, match="EC2 instance not found"):
        fetch_ec2_instance(_INSTANCE_ID)


def test_fetch_client_error_raises_runtime_error(mock_ec2_client):
    error_response = {"Error": {"Code": "UnauthorizedOperation", "Message": "Denied"}}
    mock_ec2_client.describe_instances.side_effect = ClientError(error_response, "DescribeInstances")

    with pytest.raises(RuntimeError, match="AWS ClientError"):
        fetch_ec2_instance(_INSTANCE_ID)


def test_fetch_botocore_error_raises_runtime_error(mock_ec2_client):
    mock_ec2_client.describe_instances.side_effect = BotoCoreError()

    with pytest.raises(RuntimeError, match="BotoCoreError"):
        fetch_ec2_instance(_INSTANCE_ID)


def test_fetch_empty_reservations_raises_value_error(mock_ec2_client):
    mock_ec2_client.describe_instances.return_value = {"Reservations": []}

    with pytest.raises(ValueError, match="EC2 instance not found"):
        fetch_ec2_instance(_INSTANCE_ID)

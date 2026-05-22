"""Tests for driftwatch.poller."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from driftwatch.poller import (
    PollResult,
    _FETCHERS,
    poll_all,
    poll_resource,
    register_fetcher,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_baseline(resource_id: str, resource_type: str) -> MagicMock:
    bl = MagicMock()
    bl.resource_id = resource_id
    bl.resource_type = resource_type
    return bl


# ---------------------------------------------------------------------------
# register_fetcher
# ---------------------------------------------------------------------------


def test_register_fetcher_adds_to_registry():
    @register_fetcher("_test_type")
    def _fake_fetcher(resource_id: str):
        return {"key": "value"}

    assert "_test_type" in _FETCHERS
    assert _FETCHERS["_test_type"] is _fake_fetcher
    # Cleanup so we don't pollute other tests
    del _FETCHERS["_test_type"]


# ---------------------------------------------------------------------------
# poll_resource
# ---------------------------------------------------------------------------


def test_poll_resource_success(monkeypatch):
    monkeypatch.setitem(_FETCHERS, "s3_bucket", lambda _: {"versioning_enabled": True})

    result = poll_resource("my-bucket", "s3_bucket")

    assert result.ok
    assert result.resource_id == "my-bucket"
    assert result.config == {"versioning_enabled": True}
    assert result.error is None


def test_poll_resource_unknown_type():
    result = poll_resource("some-resource", "nonexistent_type")

    assert not result.ok
    assert result.config == {}
    assert "nonexistent_type" in result.error


def test_poll_resource_fetcher_raises(monkeypatch):
    def _bad_fetcher(_):
        raise ValueError("AWS exploded")

    monkeypatch.setitem(_FETCHERS, "s3_bucket", _bad_fetcher)

    result = poll_resource("my-bucket", "s3_bucket")

    assert not result.ok
    assert "AWS exploded" in result.error
    assert result.config == {}


# ---------------------------------------------------------------------------
# poll_all
# ---------------------------------------------------------------------------


def test_poll_all_returns_one_result_per_baseline(monkeypatch):
    monkeypatch.setitem(_FETCHERS, "s3_bucket", lambda _: {"versioning_enabled": False})

    baselines = [
        _make_baseline("bucket-a", "s3_bucket"),
        _make_baseline("bucket-b", "s3_bucket"),
    ]
    results = poll_all(baselines)

    assert len(results) == 2
    assert all(isinstance(r, PollResult) for r in results)
    assert {r.resource_id for r in results} == {"bucket-a", "bucket-b"}


def test_poll_all_empty_baselines():
    assert poll_all([]) == []

"""Tests for driftwatch.cli."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from driftwatch.cli import build_parser, main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_baselines(tmp_path: Path, data: object) -> Path:
    p = tmp_path / "baselines.json"
    p.write_text(json.dumps(data))
    return p


VALID_BASELINES = [
    {
        "resource_id": "my-bucket",
        "resource_type": "s3",
        "expected_config": {"versioning": "Enabled"},
    }
]


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def test_build_parser_defaults() -> None:
    parser = build_parser()
    args = parser.parse_args(["--baselines", "some.json"])
    assert args.interval == 300
    assert args.cycles is None
    assert args.channels == ["log"]


def test_build_parser_custom_values() -> None:
    parser = build_parser()
    args = parser.parse_args(
        ["--baselines", "b.json", "--interval", "60", "--cycles", "5", "--channels", "log", "console"]
    )
    assert args.interval == 60
    assert args.cycles == 5
    assert args.channels == ["log", "console"]


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def test_main_missing_file_returns_1(tmp_path: Path) -> None:
    result = main(["--baselines", str(tmp_path / "nonexistent.json")])
    assert result == 1


def test_main_invalid_baselines_returns_1(tmp_path: Path) -> None:
    bad = _write_baselines(tmp_path, [{"bad": "data"}])
    result = main(["--baselines", str(bad)])
    assert result == 1


def test_main_success_calls_start_scheduler(tmp_path: Path) -> None:
    bl = _write_baselines(tmp_path, VALID_BASELINES)
    with patch("driftwatch.cli.start_scheduler") as mock_start:
        result = main(["--baselines", str(bl), "--cycles", "1"])
    assert result == 0
    mock_start.assert_called_once()
    _, scheduler_cfg = mock_start.call_args[0]
    assert scheduler_cfg.max_cycles == 1


def test_main_channels_forwarded(tmp_path: Path) -> None:
    bl = _write_baselines(tmp_path, VALID_BASELINES)
    with patch("driftwatch.cli.start_scheduler") as mock_start:
        main(["--baselines", str(bl), "--cycles", "1", "--channels", "console"])
    _, scheduler_cfg = mock_start.call_args[0]
    assert "console" in scheduler_cfg.alert_config.channels

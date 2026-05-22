"""Command-line entry point for driftwatch."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from driftwatch.alerter import AlertConfig
from driftwatch.baseline import load_baselines
from driftwatch.scheduler import SchedulerConfig, start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="driftwatch",
        description="Poll cloud resource configs and alert on drift.",
    )
    parser.add_argument(
        "--baselines",
        required=True,
        metavar="PATH",
        help="Path to a JSON file containing baseline definitions.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        metavar="SECONDS",
        help="Polling interval in seconds (default: 300).",
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=None,
        metavar="N",
        help="Number of polling cycles to run (omit for infinite).",
    )
    parser.add_argument(
        "--channels",
        nargs="+",
        default=["log"],
        metavar="CHANNEL",
        help="Alert channels to use, e.g. log console (default: log).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    baselines_path = Path(args.baselines)
    if not baselines_path.exists():
        logger.error("Baselines file not found: %s", baselines_path)
        return 1

    try:
        baselines = load_baselines(baselines_path)
    except (ValueError, KeyError) as exc:
        logger.error("Failed to load baselines: %s", exc)
        return 1

    alert_config = AlertConfig(channels=args.channels)
    scheduler_config = SchedulerConfig(
        interval_seconds=args.interval,
        alert_config=alert_config,
        max_cycles=args.cycles,
    )

    logger.info("Loaded %d baseline(s) from %s", len(baselines), baselines_path)
    start_scheduler(baselines, scheduler_config)
    return 0


if __name__ == "__main__":
    sys.exit(main())

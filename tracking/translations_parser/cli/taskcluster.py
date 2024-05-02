#!/usr/bin/env python3
"""
Extract information from Marian execution on Task Cluster.

Example with a local file:
    parse_tc_logs -i ./tests/data/taskcluster.log

Example reading logs from a process:
    ./tests/data/simulate_process.py | parse_tc_logs -s --verbose

Example publishing data to Weight & Biases:
    parse_tc_logs -i ./tests/data/taskcluster.log --wandb-project <project> --wandb-group <group> --wandb-run-name <run>
"""

import argparse
import logging
import os
import sys
from collections.abc import Iterator
from io import TextIOWrapper
from pathlib import Path

from translations_parser.parser import TrainingParser, logger
from translations_parser.publishers import CSVExport, Publisher
from translations_parser.utils import taskcluster_log_filter
from translations_parser.wandb import add_wandb_arguments, get_wandb_publisher


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract information from Marian execution on Task Cluster"
    )
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--input-file",
        "-i",
        help="Path to the Task Cluster log file.",
        type=Path,
        default=None,
    )
    input_group.add_argument(
        "--from-stream",
        "-s",
        help="Read lines from stdin stream.",
        action="store_true",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        help="Output directory to export training and validation data as CSV.",
        type=Path,
        default=Path(__file__).parent.parent / "output",
    )
    parser.add_argument(
        "--wandb-project",
        help="Publish the training run to a Weight & Biases project.",
        default=None,
    )
    parser.add_argument(
        "--wandb-artifacts",
        help="Directory containing training artifacts to publish on Weight & Biases.",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--wandb-group",
        help="Add the training run to a Weight & Biases group e.g. by language pair or experiment.",
        default=None,
    )
    parser.add_argument(
        "--wandb-run-name",
        help="Use a custom name for the Weight & Biases run.",
        default=None,
    )
    parser.add_argument(
        "--wandb-publication",
        action="store_true",
        help="Trigger publication on Weight & Biases. Disabled by default. Can be set though env variable WANDB_PUBLICATION=True|False",
        default=os.environ.get("WANDB_PUBLICATION", "false").lower() == "true",
    )
    parser.add_argument(
        "--taskcluster-secret",
        help="Taskcluster secret name used to store the Weight & Biases secret API Key.",
        type=str,
        default=os.environ.get("TASKCLUSTER_SECRET"),
    )
    parser.add_argument(
        "--tags",
        help="List of tags to use on Weight & Biases publication",
        type=str,
        default=["taskcluster"],
        nargs="+",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        help="Print debug messages.",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
    )

    # Extend parser with Weight & Biases CLI args
    add_wandb_arguments(parser)

    return parser.parse_args()


def boot() -> None:
    args = get_args()

    if args.loglevel:
        logger.setLevel(args.loglevel)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    lines: TextIOWrapper | Iterator[str]
    if args.input_file is None and args.from_stream is False:
        raise Exception("One of `--input-file` or `--from-stream` must be set.")
    if args.from_stream:
        lines = sys.stdin
    else:
        with args.input_file.open("r") as f:
            lines = (line.strip() for line in f.readlines())

    # Build publisher output, CSV is always enabled, Weight & Biases upon operator choice
    publishers: list[Publisher] = [CSVExport(output_dir=args.output_dir)]
    wandb_publisher = get_wandb_publisher(
        project_name=args.wandb_project,
        group_name=args.wandb_group,
        run_name=args.wandb_run_name,
        taskcluster_secret=args.taskcluster_secret,
        logs_file=args.input_file,
        artifacts=args.wandb_artifacts,
        publication=args.wandb_publication,
    )
    if wandb_publisher:
        publishers.append(wandb_publisher)

    # Use log filtering when using non-stream (for uploading past experiments)
    log_filter = taskcluster_log_filter if not args.from_stream else None

    parser = TrainingParser(
        lines,
        publishers=publishers,
        log_filter=log_filter,
    )
    parser.run()


def main() -> None:
    """
    Called from Python entrypoint
    Catch every exception when running in Taskcluster to avoid crashing real training
    """
    try:
        boot()
    except Exception as e:
        logger.error(f"Publication failed: {e}")
        if os.environ.get("MOZ_AUTOMATION") is not None:
            # Stop cleanly when in taskcluster
            sys.exit(0)
        else:
            raise

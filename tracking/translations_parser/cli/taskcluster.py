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
import sys
from collections.abc import Iterator, Sequence
from datetime import datetime
from io import TextIOWrapper
from pathlib import Path

from translations_parser.parser import TrainingParser, logger
from translations_parser.publishers import CSVExport, Publisher, WandB

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)


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
        "--verbose",
        "-v",
        help="Print debug messages.",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
    )
    return parser.parse_args()


def taskcluster_log_filter(headers: Sequence[Sequence[str]]) -> bool:
    """
    Check TC log contain a valid task header i.e. ('task', <timestamp>)
    """
    for values in headers:
        if not values or len(values) != 2:
            continue
        base, timestamp = values
        if base != "task":
            continue
        try:
            datetime.fromisoformat(timestamp.rstrip("Z"))
            return True
        except ValueError:
            continue
    return False


def main() -> None:
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

    publishers: list[Publisher] = [CSVExport(output_dir=args.output_dir)]
    if args.wandb_project:
        publishers.append(
            WandB(
                project=args.wandb_project,
                artifacts=args.wandb_artifacts,
                group=args.wandb_group,
                tags=["cli"],
                name=args.wandb_run_name,
                config={
                    "logs_file": args.input_file,
                },
            )
        )

    parser = TrainingParser(
        lines,
        publishers=publishers,
        log_filter=taskcluster_log_filter,
    )
    parser.run()

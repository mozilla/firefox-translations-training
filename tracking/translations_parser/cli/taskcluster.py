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

import taskcluster
from translations_parser.parser import TrainingParser, logger
from translations_parser.publishers import CSVExport, Publisher, WandB
from translations_parser.utils import taskcluster_log_filter

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
        "--taskcluster-secret",
        help="Taskcluster secret name used to store the Weight & Biases secret API Key.",
        type=str,
        default=os.environ.get("TASKCLUSTER_SECRET"),
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

    if args.taskcluster_secret:
        assert os.environ.get(
            "TASKCLUSTER_PROXY_URL"
        ), "When using `--taskcluster-secret`, `TASKCLUSTER_PROXY_URL` environment variable must be set too."
        secrets = taskcluster.Secrets({"rootUrl": os.environ["TASKCLUSTER_PROXY_URL"]})

        try:
            wandb_secret = secrets.get(args.taskcluster_secret)
            wandb_token = wandb_secret["secret"]["token"]
        except Exception as e:
            raise Exception(
                f"Weight & Biases secret API Key retrieved from Taskcluster is malformed: {e}"
            )

        os.environ.setdefault("WANDB_API_KEY", wandb_token)

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

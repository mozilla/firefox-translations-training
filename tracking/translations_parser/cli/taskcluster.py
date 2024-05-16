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
import tempfile
from collections.abc import Iterator
from io import TextIOWrapper
from pathlib import Path

import yaml

import taskcluster
from translations_parser.parser import TrainingParser, logger
from translations_parser.publishers import CSVExport, Publisher
from translations_parser.utils import taskcluster_log_filter
from translations_parser.wandb import add_wandb_arguments, get_wandb_publisher

queue = taskcluster.Queue({"rootUrl": "https://firefox-ci-tc.services.mozilla.com"})


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
        "--verbose",
        "-v",
        help="Print debug messages.",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
    )
    parser.add_argument(
        "--publish-group-logs",
        help=("Enable publishing a group_logs fake run with the experiment configuration."),
        action="store_true",
        default=False,
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

    if args.publish_group_logs:
        logger.info("Publishing experiment config to a 'group_logs' fake run.")

        # Retrieve experiment configuration from task group
        task_id = os.environ.get("TASK_ID")
        if not task_id:
            raise Exception("Group logs publication can only run in taskcluster")
        task = queue.task(task_id)
        group_id = task["taskGroupId"]
        # Ensure task group is readable
        queue.getTaskGroup(group_id)
        task_group = queue.task(group_id)
        config = task_group.get("extra", {}).get("action", {}).get("context", {}).get("input")

        with tempfile.TemporaryDirectory() as temp_dir:
            logs_folder = Path(temp_dir) / "logs"
            config_path = Path(temp_dir) / "experiments" / project_name / group_name / "config.yml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            parents = str(logs_folder.resolve()).strip().split("/")
            with config_path.open("w") as config_file:
                yaml.dump(config, config_file)
            WandB.publish_group_logs(parents, project_name, group_name, existing_runs=[])


def main() -> None:
    """
    Entry point for the `parse_tc_logs` script.
    Catch every exception when running in Taskcluster to avoid crashing real training
    """
    try:
        boot()
    except Exception:
        logger.exception("Publication failed")
        if os.environ.get("MOZ_AUTOMATION") is not None:
            # Stop cleanly when in taskcluster
            sys.exit(0)
        else:
            raise

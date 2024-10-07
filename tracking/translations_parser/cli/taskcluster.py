#!/usr/bin/env python3
"""
Extract information from Marian execution on Taskcluster.

Example with a local file:
    parse_tc_logs --input-file ./tests/data/taskcluster.log

Example reading logs from a process:
    ./tests/data/simulate_process.py | parse_tc_logs --from-stream --verbose

Example publishing data to Weight & Biases:
    parse_tc_logs --input-file ./tests/data/taskcluster.log --wandb-project <project> --wandb-group <group> --wandb-run-name <run>
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
from translations_parser.publishers import CSVExport, Publisher
from translations_parser.utils import (
    publish_group_logs_from_tasks,
    suffix_from_group,
    taskcluster_log_filter,
)
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
        help=(
            "Enable publishing a group_logs fake run with the experiment configuration."
            "This option requires W&B publication to be enabled, otherwise it will be ignored."
        ),
        action="store_true",
        default=False,
    )

    # Extend parser with Weight & Biases CLI args
    add_wandb_arguments(parser)

    return parser.parse_args()


def is_running_in_ci():
    """
    Determine if this run is being done in CI.
    """
    task_id = os.environ.get("TASK_ID")
    if not task_id:
        return False

    logger.info(f'Fetching the experiment for task "{task_id}" to check if this is running in CI.')
    queue = taskcluster.Queue({"rootUrl": os.environ["TASKCLUSTER_PROXY_URL"]})
    task = queue.task(task_id)
    group_id = task["taskGroupId"]
    task_group = queue.task(group_id)
    # e.g,. "github-pull-request", "action", "github-push"
    tasks_for = task_group.get("extra", {}).get("tasks_for")
    return tasks_for != "action"


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
    elif args.publish_group_logs:
        logger.warning(
            "Ignoring --publish-group-logs option as Weight & Biases publication is disabled."
        )

    # Publish experiment configuration before parsing the training logs
    if wandb_publisher and args.publish_group_logs:
        logger.info("Publishing experiment config to a 'group_logs' fake run.")
        # Retrieve experiment configuration from the task group
        task_id = os.environ.get("TASK_ID")
        if not task_id:
            raise Exception("Group logs publication can only run in taskcluster")
        task = queue.task(task_id)
        group_id = task["taskGroupId"]
        # Ensure task group is readable
        queue.getTaskGroup(group_id)
        task_group = queue.task(group_id)
        config = task_group.get("extra", {}).get("action", {}).get("context", {}).get("input")
        publish_group_logs_from_tasks(
            project=wandb_publisher.project,
            group=wandb_publisher.group,
            config=config,
            suffix=suffix_from_group(group_id),
        )

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
    Entry point for the `parse_tc_logs` script.
    Catch every exception when running in Taskcluster to avoid crashing real training
    """
    try:
        boot()
    except Exception as exception:
        if os.environ.get("MOZ_AUTOMATION") is None:
            logger.exception("Publication failed when running locally.")
            raise exception
        elif is_running_in_ci():
            logger.exception("Publication failed when running in CI.")
            raise exception
        else:
            logger.exception(
                "Publication failed! The error is ignored to not break training, but it should be fixed."
            )
            sys.exit(0)

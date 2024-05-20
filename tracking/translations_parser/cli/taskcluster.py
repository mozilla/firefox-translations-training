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
from translations_parser.utils import build_task_name, taskcluster_log_filter


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
    return parser.parse_args()


def get_wandb_token(secret_name):
    """
    Retrieve the Weight & Biases token from Taskcluster secret
    """
    secrets = taskcluster.Secrets({"rootUrl": os.environ["TASKCLUSTER_PROXY_URL"]})

    try:
        wandb_secret = secrets.get(secret_name)
        return wandb_secret["secret"]["token"]
    except Exception as e:
        raise Exception(
            f"Weight & Biases secret API Key retrieved from Taskcluster is malformed: {e}"
        )


def get_wandb_names():
    """
    Find the various names needed to publish on Weight & Biases using
    the taskcluster task & group payloads
    """
    task_id = os.environ.get("TASK_ID")
    if not task_id:
        raise Exception("Weight & Biases name detection can only run in taskcluster")

    # Load task & group definition
    # CI task groups do not expose any configuration, so we must use default values
    queue = taskcluster.Queue({"rootUrl": os.environ["TASKCLUSTER_PROXY_URL"]})
    task = queue.task(task_id)
    _, task_name = build_task_name(task)
    group_id = task["taskGroupId"]
    task_group = queue.task(group_id)
    config = task_group.get("extra", {}).get("action", {}).get("context", {}).get("input")
    if config is None:
        logger.warn(
            f"Experiment configuration missing on {group_id} @ extra/action/context/input, fallback to CI values"
        )
        experiment = {
            "src": "ru",
            "trg": "en",
            "name": "ci",
        }
    else:
        experiment = config["experiment"]

    # Build project, group and run names
    return (
        f'{experiment["src"]}-{experiment["trg"]}',
        f'{experiment["name"]}_{group_id}',
        task_name,
    )


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

    # Load secret from Taskcluster and auto-configure naming
    if args.taskcluster_secret:
        assert os.environ.get(
            "TASKCLUSTER_PROXY_URL"
        ), "When using `--taskcluster-secret`, `TASKCLUSTER_PROXY_URL` environment variable must be set too."

        # Weight and Biases client use environment variable to read the token
        os.environ.setdefault("WANDB_API_KEY", get_wandb_token(args.taskcluster_secret))

        project_name, group_name, run_name = get_wandb_names()
    else:
        # Fallback to CLI args for names
        project_name = args.wandb_project
        group_name = args.wandb_group
        run_name = args.wandb_run_name

    # Enable publication on weight and biases when project is set
    # But prevent running when explicitly disabled by operator
    publishers: list[Publisher] = [CSVExport(output_dir=args.output_dir)]
    if not args.wandb_publication:
        logger.info(
            "Skip weight & biases publication as requested by operator through WANDB_PUBLICATION"
        )
    elif not project_name:
        logger.info("Skip weight & biases publication as project name is not set")
    else:
        publishers.append(
            WandB(
                project=project_name,
                group=group_name,
                name=run_name,
                artifacts=args.wandb_artifacts,
                tags=args.tags,
                config={
                    "logs_file": args.input_file,
                },
            )
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
    except Exception:
        logger.exception("Publication failed")
        if os.environ.get("MOZ_AUTOMATION") is not None:
            # Stop cleanly when in taskcluster
            sys.exit(0)
        else:
            raise

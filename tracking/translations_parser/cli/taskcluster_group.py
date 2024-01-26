#!/usr/bin/env python3
"""
Track training experiments from a Taskcluster group and publish them to Weight and Biases.

Example:
    track_tc_group --group-id=<group_id>
"""

import argparse
import logging

import taskcluster
from taskcluster.download import downloadArtifactToBuf
from translations_parser.parser import TrainingParser, logger
from translations_parser.publishers import WandB

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)

KIND_TAG_TARGET = ("train", "finetune")


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Track training experiments from a Taskcluster group"
    )
    parser.add_argument(
        "group_id",
        help="ID of the Taskcluster training task group.",
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


def get_logs(task, queue):
    """Retrieve training logs from Taskcluster"""
    task_id = task["status"]["taskId"]
    logger.info(f"Downloading logs for task {task_id}")
    log, _ = downloadArtifactToBuf(
        taskId=task_id,
        name="public/build/train.log",
        queueService=queue,
    )
    return log.tobytes().decode().split("\n")


def main() -> None:
    args = get_args()

    if args.loglevel:
        logger.setLevel(args.loglevel)

    logger.info(f"Retrieving task group {args.group_id}")
    queue = taskcluster.Queue({"rootUrl": "https://firefox-ci-tc.services.mozilla.com"})
    # Ensure task group is readable
    queue.getTaskGroup(args.group_id)
    # Read project and experiment name
    task_group = queue.task(args.group_id)
    config = task_group["extra"]["action"]["context"]["input"]
    experiment = config["experiment"]
    project = f"{experiment['src']}-{experiment['trg']}"
    group_name = f"{experiment['name']}_{args.group_id}"

    logger.info(f"Listing completed tasks from group {args.group_id}")
    resp = queue.listTaskGroup(args.group_id)
    tasks = resp["tasks"]
    continuation_token = resp.get("continuationToken")
    while continuation_token:
        # Results may be returned in multiple pages
        # https://docs.taskcluster.net/docs/reference/platform/queue/api#listTaskGroup
        resp = queue.listTaskGroup(args.group_id, {"continuationToken": continuation_token})
        tasks.extend(resp["tasks"])
        continuation_token = resp.get("continuationToken")
    tasks = [
        t
        for t in tasks
        if t["status"]["state"] == "completed"
        and "vocab" not in t["task"]["tags"]["kind"]
        and any(t["task"]["tags"]["kind"].startswith(target) for target in KIND_TAG_TARGET)
    ]
    if not tasks:
        raise Exception(f"No valid training task found for task group {args.group_id}")

    logger.info(f"Found {len(tasks)} completed training tasks")

    for task in tasks:
        lines = get_logs(task, queue)
        parser = TrainingParser(
            lines,
            publishers=[
                WandB(
                    project=project,
                    group=group_name,
                    tags=["taskcluster"],
                    name=task["task"]["tags"]["kind"],
                    config=config,
                )
            ],
            skip_marian_context=True,
            # TODO parse metrics
            metrics=None,
        )
        parser.run(),

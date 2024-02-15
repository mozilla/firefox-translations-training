#!/usr/bin/env python3
"""
Track training experiments from a Taskcluster group and publish them to Weight and Biases.

Example:
    track_tc_group --group-id=<group_id>
"""

import argparse
import logging
import re
import tempfile
from collections import defaultdict
from pathlib import Path

import yaml

import taskcluster
from taskcluster.download import downloadArtifactToBuf, downloadArtifactToFile
from translations_parser.data import Metric
from translations_parser.parser import TrainingParser, logger
from translations_parser.publishers import WandB

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)

KIND_TAG_TARGET = ("train", "finetune")
MULTIPLE_TRAIN_SUFFIX = re.compile(r"(-\d+)/\d+$")
queue = taskcluster.Queue({"rootUrl": "https://firefox-ci-tc.services.mozilla.com"})


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


def get_logs(task: dict) -> list[str]:
    """Retrieve training logs from Taskcluster"""
    task_id = task["status"]["taskId"]
    logger.info(f"Downloading logs for task {task_id}")
    log, _ = downloadArtifactToBuf(
        taskId=task_id,
        name="public/build/train.log",
        queueService=queue,
    )
    return log.tobytes().decode().split("\n")


def publish_task(project: str, group: str, name: str, task: dict, metrics: list[Metric]) -> None:
    parser = TrainingParser(
        get_logs(task),
        publishers=[
            WandB(
                project=project,
                group=group,
                name=name,
                tags=["taskcluster"],
            )
        ],
        metrics=metrics,
    )
    parser.run()


def get_metrics_from_task(task: dict) -> list[Metric]:
    task_id = task["status"]["taskId"]
    logger.info(f"Retrieving artifacts from evaluation task {task_id}")
    metrics = []
    for artifact in queue.listLatestArtifacts(task_id)["artifacts"]:
        if not artifact["name"].endswith(".metrics"):
            continue
        log, _ = downloadArtifactToBuf(
            taskId=task_id,
            name=artifact["name"],
            queueService=queue,
        )

        tag = task["task"]["tags"]["label"]
        # Remove eventual slashes (e.g. <task_tag>-1/2) that cannot be written to the filesystem
        tag = MULTIPLE_TRAIN_SUFFIX.sub("", tag)

        with tempfile.TemporaryDirectory() as d:
            file = Path(d) / f"{tag}.txt"
            with file.open("wb") as f:
                f.write(log.tobytes())
                f.flush()
                metrics.append(Metric.from_file(Path(f.name), sep="-"))
    return metrics


def main() -> None:
    args = get_args()

    if args.loglevel:
        logger.setLevel(args.loglevel)

    logger.info(f"Retrieving task group {args.group_id}")
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
    # Map tasks by categories
    tasks_groups = defaultdict(list)
    for task in tasks:
        # Exclude non completed or vocab tasks
        if task["status"]["state"] == "completed" and "vocab" not in task["task"]["tags"]["kind"]:
            name = task["task"]["tags"]["kind"]
            prefix = name.split("-")[0]
            if prefix == "train":
                # Remove "train-" prefix from training task only to avoid duplicates
                name = name[6:]
            # Teacher training may run multiple times (e.g. "-1/2" prefix)
            suffix = ""
            label = task["task"]["tags"].get("label")
            if label and (re_match := MULTIPLE_TRAIN_SUFFIX.search(label)):
                (suffix,) = re_match.groups()
            task["name"] = name + suffix
            tasks_groups[prefix].append(task)

    train_tasks = sum(
        [tasks for key, tasks in tasks_groups.items() if key in KIND_TAG_TARGET], start=[]
    )

    if not train_tasks:
        logger.warning(f"No completed training task found for group {args.group_id}")
    else:
        logger.info(f"Found {len(train_tasks)} completed training tasks")

    metrics_tasks = {task["status"]["taskId"]: task for task in tasks_groups["evaluate"]}

    for task in train_tasks:
        # Associate metrics to each runs (evaluate tasks that depends on the training task)
        dependent_tasks = []
        for eval_id, eval_task in metrics_tasks.items():
            if task["status"]["taskId"] in eval_task["task"]["dependencies"]:
                dependent_tasks.append(eval_id)
        metrics = sum(
            [get_metrics_from_task(metrics_tasks.pop(task_id)) for task_id in dependent_tasks],
            start=[],
        )
        run = task["name"]
        publish_task(
            project=project,
            group=group_name,
            name=run,
            task=task,
            metrics=metrics,
        )

    # Group and publish missing runs with metrics via the logs publication
    with tempfile.TemporaryDirectory() as d:
        logs_folder = Path(d) / "logs"
        eval_folder = logs_folder / project / group_name / "eval"
        eval_folder.mkdir(parents=True, exist_ok=True)
        for task in metrics_tasks.values():
            filename = task["task"]["tags"]["label"]
            # evaluate-teacher-flores-flores_aug-typos_devtest-lt-en-1/2
            with (eval_folder / f"{filename}.log").open("wb") as f:
                downloadArtifactToFile(
                    f,
                    taskId=task["status"]["taskId"],
                    name="public/logs/live.log",
                    queueService=queue,
                )
        # Dump experiment config so it is published on group_logs
        config_path = Path(d) / "experiments" / project / group_name / "config.yml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with config_path.open("w") as f:
            yaml.dump(config, f)

        parents = str(logs_folder.resolve()).strip().split("/")
        WandB.publish_group_logs(parents, project, group_name, existing_runs=[], tag_sep="-")

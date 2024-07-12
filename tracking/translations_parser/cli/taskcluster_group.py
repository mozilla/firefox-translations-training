#!/usr/bin/env python3
"""
Track training experiments from a Taskcluster group and publish them to Weight and Biases.

Example:
    track_tc_group --group-id=<group_id>
"""

import argparse
import logging
import tempfile
from collections import defaultdict
from pathlib import Path

import wandb

import taskcluster
from taskcluster.download import downloadArtifactToBuf
from translations_parser.data import Metric
from translations_parser.parser import TrainingParser, logger
from translations_parser.publishers import WandB
from translations_parser.utils import (
    MULTIPLE_TRAIN_SUFFIX,
    build_task_name,
    parse_task_label,
    publish_group_logs_from_tasks,
    suffix_from_group,
)

KIND_TAG_TARGET = ("train", "finetune")
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
        "--no-recursive-lookup",
        help="Disable group traversal from provided group_id tasks dependencies.",
        action="store_true",
    )
    parser.add_argument(
        "--override-runs",
        help="Override runs on Weight & Biases.",
        action="store_true",
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
    try:
        log, _ = downloadArtifactToBuf(
            taskId=task_id,
            name="public/build/train.log",
            queueService=queue,
        )
    except Exception as e:
        logger.error(f"Could not retrieve logs: {e}")
        return []
    return log.tobytes().decode().split("\n")


def publish_task(
    *, project: str, group: str, name: str, suffix: str, task: dict, metrics: list[Metric]
) -> None:
    logs = get_logs(task)
    if not logs:
        logger.warning(f"Skipping publication of training task {name}")
        return
    parser = TrainingParser(
        logs,
        publishers=[
            WandB(
                project=project,
                group=group,
                name=name,
                suffix=suffix,
                tags=["taskcluster-offline"],
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

        with tempfile.TemporaryDirectory() as temp_dir:
            file = Path(temp_dir) / f"{tag}.txt"
            with file.open("wb") as log_file:
                log_file.write(log.tobytes())
                log_file.flush()
                metrics.append(Metric.from_file(Path(log_file.name)))

    return metrics


def filter_task(task: dict) -> tuple[str, dict] | tuple[None, None]:
    if task["status"]["state"] == "completed" and "vocab" not in task["task"]["tags"]["kind"]:
        try:
            prefix, task["name"] = build_task_name(task["task"])
        except ValueError:
            # Task label may be unrelated to training or validation
            label = task["task"].get("tags", {}).get("label", "unknown")
            logger.debug(f"Skipping task with label {label}")
        else:
            return prefix, task

    return None, None


def list_training_tasks(group_id: str, grouped_tasks: dict[str, list[dict]]) -> list[list[dict]]:
    training_tasks = sum(
        [tasks for key, tasks in grouped_tasks.items() if key in KIND_TAG_TARGET], start=[]
    )

    if not training_tasks:
        logger.warning(f"No completed training task found for group {group_id}")
    else:
        logger.info(f"Found {len(training_tasks)} completed training tasks")

    return training_tasks


def list_metrics_tasks(group_id: str, grouped_tasks: dict[str, list[dict]]) -> dict[str, dict]:
    metrics_tasks = {task["status"]["taskId"]: task for task in grouped_tasks["evaluate"]}

    if not metrics_tasks:
        logger.warning(f"No completed metrics task found for group {group_id}")
    else:
        logger.info(f"Found {len(metrics_tasks)} completed metrics tasks")

    return metrics_tasks


def list_completed_tasks(group_id: str) -> dict[str, list[dict]]:
    logger.info(f"Listing completed tasks from group {group_id}")

    response = queue.listTaskGroup(group_id)
    tasks = response["tasks"]
    continuation_token = response.get("continuationToken")
    while continuation_token:
        # Results may be returned in multiple pages
        # https://docs.taskcluster.net/docs/reference/platform/queue/api#listTaskGroup
        response = queue.listTaskGroup(group_id, {"continuationToken": continuation_token})
        tasks.extend(response["tasks"])
        continuation_token = response.get("continuationToken")

    # Map tasks by categories
    grouped_tasks = defaultdict(list)
    for task in tasks:
        # Exclude non completed or vocab tasks
        prefix, filtered_task = filter_task(task)
        if filtered_task:
            grouped_tasks[prefix].append(filtered_task)

    return grouped_tasks


def publish_task_group(group_id: str, override: bool = False) -> None:
    logger.info(f"Retrieving task group {group_id}")

    # Ensure task group is readable
    queue.getTaskGroup(group_id)

    # Read project and experiment name from task group configuration
    task_group = queue.task(group_id)
    config = task_group.get("extra", {}).get("action", {}).get("context", {}).get("input")

    # If the task group does not have a training configuration, we can skip its publication
    if config is None:
        logger.warning(
            f"Task group {group_id} cannot be published to WandB: "
            "configuration missing @ extra/action/context/input"
        )
        return

    experiment = config["experiment"]
    project_name = f'{experiment["src"]}-{experiment["trg"]}'
    group_name = f'{experiment["name"]}_{group_id}'

    grouped_tasks = list_completed_tasks(group_id)
    training_tasks = list_training_tasks(group_id, grouped_tasks)
    metrics_tasks = list_metrics_tasks(group_id, grouped_tasks)

    if not training_tasks:
        logger.warning(f"Skipping task group {group_id} as it is empty")
        return

    logger.info(f"Processing group {group_name}")

    if override:
        existing_runs = list(wandb.Api().runs(project_name, filters={"group": group_name}))
        for run in existing_runs:
            logger.warning(f"Deleting existing run {run.display_name}.")
            run.delete()

    # Publish training tasks as runs
    for training_task in training_tasks:
        # Associate metrics to each runs (evaluate tasks that depends on the training task)
        dependent_tasks = []
        for eval_id, eval_task in metrics_tasks.items():
            eval_label = eval_task["task"]["tags"].get("label", "")

            try:
                model_name = parse_task_label(eval_label).model
            except ValueError:
                continue

            # Evaluation tasks must be a dependency of the run and match its name
            if (
                training_task["status"]["taskId"] in eval_task["task"]["dependencies"]
                and model_name == training_task["name"]
            ):
                dependent_tasks.append(eval_id)

        metrics = sum(
            [
                get_metrics_from_task(metrics_tasks.pop(dependent_task_id))
                for dependent_task_id in dependent_tasks
            ],
            start=[],
        )

        publish_task(
            project=project_name,
            group=group_name,
            suffix=suffix_from_group(group_id),
            name=training_task["name"],
            task=training_task,
            metrics=metrics,
        )

    # Group and publish remaining metrics tasks via the logs publication
    publish_group_logs_from_tasks(
        project=project_name,
        group=group_name,
        metrics_tasks=metrics_tasks,
        config=config,
    )


def list_dependent_group_ids(task_id: str, known: set[str]):
    task = queue.task(task_id)

    # Browse task dependencies
    for dependent_task_id in task["dependencies"]:
        dependent_status = queue.status(dependent_task_id)

        group_id = dependent_status["status"]["taskGroupId"]
        if group_id in known:
            continue

        yield group_id
        known.add(group_id)

        # Shared instance of `known` to propagate discovered groups in real time across all recursion branches
        yield from list_dependent_group_ids(dependent_task_id, known)


def main() -> None:
    args = get_args()

    if args.loglevel:
        logger.setLevel(args.loglevel)

    groups_ids = {args.group_id}
    if not args.no_recursive_lookup:
        logger.info(f"Retrieving related groups from {args.group_id} training tasks dependencies")

        completed_tasks = list_completed_tasks(args.group_id)
        training_tasks = list_training_tasks(args.group_id, completed_tasks)
        for training_task in training_tasks:
            dependent_ids = list_dependent_group_ids(
                training_task["status"]["taskId"], {*groups_ids}
            )
            groups_ids.update(dependent_ids)

        logger.info(
            f"Found {len(groups_ids) - 1} additional groups to browse for WandB publication"
        )
    else:
        logger.info(
            "--no-recursive-lookup option is set, only the provided group will be browsed for WandB publication"
        )

    for group_id in groups_ids:
        publish_task_group(group_id, override=args.override_runs)

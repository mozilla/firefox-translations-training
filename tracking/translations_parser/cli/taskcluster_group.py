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
from translations_parser.utils import extract_dataset_from_tag

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
        "--no-recursive-lookup",
        help="Disable group traversal from provided group_id tasks dependencies.",
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

        with tempfile.TemporaryDirectory() as temp_dir:
            file = Path(temp_dir) / f"{tag}.txt"
            with file.open("wb") as log_file:
                log_file.write(log.tobytes())
                log_file.flush()
                metrics.append(Metric.from_file(Path(log_file.name), sep="-"))

    return metrics


def filter_task(task: dict) -> tuple[str, dict] | tuple[None, None]:
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


def list_metrics_tasks(
    group_id: str, grouped_tasks: dict[str, list[dict]]
) -> list[dict[str, dict]]:
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


def publish_task_group(group_id: str) -> None:
    logger.info(f"Retrieving task group {group_id}")

    # Ensure task group is readable
    queue.getTaskGroup(group_id)

    # Read project and experiment name from task group configuration
    task_group = queue.task(group_id)
    config = task_group.get("extra", {}).get("action", {}).get("context", {}).get("input")

    # If the task group does not have a training configuration, we can skip its publication
    if config is None:
        logger.warning(f"Task group {group_id} cannot be published to WandB")
        return

    experiment = config["experiment"]
    project_name = f'{experiment["src"]}-{experiment["trg"]}'
    group_name = f'{experiment["name"]}_{group_id}'

    grouped_tasks = list_completed_tasks(group_id)
    metrics_tasks = list_metrics_tasks(group_id, grouped_tasks)

    # Publish training tasks as runs
    for training_task in list_training_tasks(group_id, grouped_tasks):
        # Associate metrics to each runs (evaluate tasks that depends on the training task)
        dependent_tasks = []
        for eval_id, eval_task in metrics_tasks.items():
            eval_label = eval_task["task"]["tags"].get("label", "")

            try:
                model_name, _, _ = extract_dataset_from_tag(eval_label, sep="-")
            except ValueError:
                continue

            if eval_label and (re_match := MULTIPLE_TRAIN_SUFFIX.search(eval_label)):
                (suffix,) = re_match.groups()
                model_name += suffix

            # Evaluation tasks may be named finetuned instead of finetune
            model_name = model_name.replace("finetuned", "finetune")

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
            name=training_task["name"],
            task=training_task,
            metrics=metrics,
        )

    # Group and publish remaining metrics tasks via the logs publication
    with tempfile.TemporaryDirectory() as temp_dir:
        logs_folder = Path(temp_dir) / "logs"
        eval_folder = logs_folder / project_name / group_name / "eval"
        eval_folder.mkdir(parents=True, exist_ok=True)

        for metrics_task in metrics_tasks.values():
            filename = metrics_task["task"]["tags"]["label"]
            # evaluate-teacher-flores-flores_aug-typos_devtest-lt-en-1/2
            with (eval_folder / f"{filename}.log").open("wb") as log_file:
                downloadArtifactToFile(
                    log_file,
                    taskId=metrics_task["status"]["taskId"],
                    name="public/logs/live.log",
                    queueService=queue,
                )

        # Dump experiment config so it is published on group_logs
        config_path = Path(temp_dir) / "experiments" / project_name / group_name / "config.yml"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with config_path.open("w") as config_file:
            yaml.dump(config, config_file)

        parents = str(logs_folder.resolve()).strip().split("/")
        WandB.publish_group_logs(parents, project_name, group_name, existing_runs=[], tag_sep="-")


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
        publish_task_group(group_id)

#!/usr/bin/env python3
"""
Publish multiple experiments to Weight & Biases.

Example:
    parse_experiment_dir -d ./tests/data/experiments
"""

import argparse
import logging
import os
from itertools import groupby
from pathlib import Path

import wandb

from translations_parser.data import Metric
from translations_parser.parser import TrainingParser
from translations_parser.publishers import WandB

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish multiple experiments to Weight & Biases")
    parser.add_argument(
        "--directory",
        "-d",
        help="Path to the experiments directory.",
        type=Path,
        default=Path(Path(os.getcwd())),
    )
    return parser.parse_args()


def parse_experiment(
    project: str,
    group: str,
    name: str,
    logs_file: Path,
    metrics_dir: Path | None = None,
) -> None:
    """
    Parse logs from a Taskcluster dump and publish data to W&B.
    If a metrics directory is set, initially read and publish each `.metrics` values.
    """
    metrics = []
    if metrics_dir:
        for metrics_file in metrics_dir.glob("*.metrics"):
            metrics.append(Metric.from_file(metrics_file))

    with logs_file.open("r") as f:
        lines = (line.strip() for line in f.readlines())
    parser = TrainingParser(
        lines,
        metrics=metrics,
        publishers=[
            WandB(
                project=project,
                name=name,
                group=group,
                config={"logs_file": logs_file},
            )
        ],
    )
    parser.run()


def publish_group_logs(
    project: str,
    group: str,
    logs_dir: Path,
    metrics_dir: Path,
) -> None:
    """
    Publish all files within `logs_dir` to W&B artifacts for a specific group.
    A fake W&B run named `group_logs` is created to publish artifacts.
    If a metrics directory is set, initially read and publish each `.metrics` values.
    """
    publisher = WandB(
        project=project,
        group=group,
        name="group_logs",
    )
    publisher.wandb = wandb.init(
        project=project,
        group=group,
        name="group_logs",
    )
    if publisher.wandb is None:
        return
    # Add "speed" metrics
    metrics = []
    for metrics_file in metrics_dir.glob("*.metrics"):
        metrics.append(Metric.from_file(metrics_file))
    if metrics:
        publisher.handle_metrics(metrics)
    # Add logs dir content as artifacts
    if logs_dir.is_dir():
        artifact = wandb.Artifact(name=group, type="logs")
        artifact.add_dir(local_path=str(logs_dir.resolve()))
        publisher.wandb.log_artifact(artifact)
    publisher.wandb.finish()


def main() -> None:
    args = get_args()
    directory = args.directory
    # Ignore files with a different name than "train.log"
    file_groups = {
        path: list(files)
        for path, files in groupby(
            sorted(directory.glob("**/train.log")), lambda path: path.parent
        )
    }
    logger.info(f"Reading {len(file_groups)} train.log data")
    prefix = os.path.commonprefix([path.parts for path in file_groups])
    if "models" in prefix:
        prefix = prefix[: prefix.index("models") + 1]

    last_index = None
    for index, (path, files) in enumerate(file_groups.items(), start=1):
        logger.info(f"Parsing folder {path.resolve()}")
        parents = path.parts[len(prefix) :]
        if len(parents) < 3:
            logger.warning(f"Skipping folder {path.resolve()}: Unexpected folder structure")
            continue
        project, group, *name = parents
        base_name = name[0]
        name = "_".join(name)

        # Publish a run for each file inside that group
        for file in files:
            # Also publish metric files when available
            metrics_path = Path("/".join([*prefix, project, group, "evaluation", base_name]))
            metrics_dir = metrics_path if metrics_path.is_dir() else None
            if metrics_dir is None:
                logger.warning("Evaluation metrics files not found, skipping.")
            try:
                parse_experiment(project, group, name, file, metrics_dir=metrics_dir)
            except Exception as e:
                logger.error(f"An exception occured parsing {file}: {e}")

        # Try to publish related log files to the group on a last run named "group_logs"
        if index == len(file_groups) or last_index and last_index != (project, group):
            last_project, last_group = (
                last_index
                if last_index
                # May occur when handling a single run
                else (project, group)
            )
            logs_dir = Path("/".join([*prefix[:-1], "logs", last_project, last_group]))
            metrics_dir = Path(
                "/".join([*prefix, last_project, last_group, "evaluation", "speed"])
            )
            if logs_dir.exists() or next(metrics_dir.glob("*.metrics"), None) is None:
                logger.info(
                    f"Publishing '{last_project}' group '{last_group}' metrics and files to a last fake run 'group_logs'"
                )
                publish_group_logs(last_project, last_group, logs_dir, metrics_dir)
            else:
                logger.warning(
                    "No extra logs nor metrics found for this project, skipping 'group_logs' fake run."
                )
        last_index = (project, group)

#!/usr/bin/env python3
"""
Publish multiple experiments to Weight & Biases.

Example:
    parse_experiment_dir -d ./tests/data/experiments
"""

import argparse
import logging
import os
from enum import Enum
from itertools import groupby
from pathlib import Path

from translations_parser.data import Metric
from translations_parser.parser import TrainingParser
from translations_parser.publishers import WandB
from translations_parser.utils import parse_task_label, parse_gcp_metric

logger = logging.getLogger(__name__)


class ExperimentMode(Enum):
    SNAKEMAKE = "snakemake"
    TASKCLUSTER = "taskcluster"


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish multiple experiments to Weight & Biases")
    parser.add_argument(
        "--mode",
        "-m",
        help="Mode to publish experiments.",
        type=ExperimentMode,
        choices=ExperimentMode,
        metavar=[e.value for e in ExperimentMode],
        required=True,
    )
    parser.add_argument(
        "--directory",
        "-d",
        help="Path to the experiments directory.",
        type=Path,
        default=Path(Path(os.getcwd())),
    )
    return parser.parse_args()


def parse_experiment(
    *,
    project: str,
    group: str,
    name: str,
    suffix: str,
    logs_file: Path,
    metrics_dir: Path | None = None,
    mode=ExperimentMode,
) -> None:
    """
    Parse logs from a Taskcluster dump and publish data to W&B.
    If a metrics directory is set, initially read and publish each `.metrics` values.
    """
    metrics = []
    if metrics_dir:
        for metrics_file in metrics_dir.glob("*.metrics"):
            try:
                metric_attrs = parse_gcp_metric(metrics_file.stem)
            except ValueError:
                logger.error(f"Error parsing metric from GCP: {metrics_file.stem}. Skipping.")
            else:
                metrics.append(
                    Metric.from_file(
                        metrics_file,
                        importer=metric_attrs.importer,
                        dataset=metric_attrs.dataset,
                        augmentation=metric_attrs.augmentation,
                    )
                )

    with logs_file.open("r") as f:
        lines = (line.strip() for line in f.readlines())
    parser = TrainingParser(
        lines,
        metrics=metrics,
        publishers=[
            WandB(
                project=project,
                group=group,
                name=name,
                suffix=suffix,
            )
        ],
    )
    parser.run()


def main() -> None:
    args = get_args()
    directory = args.directory
    mode = args.mode

    # Ignore files with a different name than "train.log"
    train_files = sorted(directory.glob("**/train.log"))

    logger.info(f"Reading {len(train_files)} train.log data")
    prefix = os.path.commonprefix([path.parts for path in train_files])

    # Move on top of the main models (Snakemake) or logs (Taskcluster) folder
    if "models" in prefix:
        prefix = prefix[: prefix.index("models")]
    if "logs" in prefix:
        prefix = prefix[: prefix.index("logs")]

    # First parent folder correspond to the run name, second one is the group
    groups = groupby(train_files, lambda path: path.parent.parent)

    for path, files in groups:
        logger.info(f"Parsing folder {path.resolve()}")
        *_, project, group = path.parts
        if mode == ExperimentMode.TASKCLUSTER:
            if len(group) < 22:
                logger.error(
                    f"Skip folder {group} as it cannot contain a task group ID (too few caracters)."
                )
                continue
            suffix = f"_{group[-22:-17]}"
        else:
            # Use the full experiment name as a suffix for old Snakemake experiments
            suffix = f"_{group}"

        # Publish a run for each file inside that group
        published_runs = []
        for file in files:
            try:
                tag = f"train-{file.parent.name}"
                name = parse_task_label(tag).model
            except ValueError:
                logger.error(f"Invalid tag extracted from file @{path}: {tag}")
                continue
            logger.info(f"Handling training task {name}")

            # Also publish metric files when available
            metrics_path = Path(
                "/".join([*prefix, "models", project, group, "evaluation", file.parent.name])
            )
            metrics_dir = metrics_path if metrics_path.is_dir() else None
            if metrics_dir is None:
                logger.warning(f"Evaluation metrics files not found for {name}.")

            try:
                parse_experiment(
                    project=project,
                    group=group,
                    name=name,
                    suffix=suffix,
                    logs_file=file,
                    metrics_dir=metrics_dir,
                    mode=mode,
                )
            except Exception as e:
                logger.error(f"An exception occured parsing training file {file}: {e}")
            else:
                published_runs.append(name)

        # Try to publish related log files to the group on a last run named "group_logs"
        logger.info(
            f"Publishing '{project}/{group}' evaluation metrics and files (fake run 'group_logs')"
        )
        WandB.publish_group_logs(
            logs_parent_folder=[*prefix, "logs"],
            project=project,
            group=group,
            suffix=suffix,
            existing_runs=published_runs,
            snakemake=(mode == ExperimentMode.SNAKEMAKE.value),
        )

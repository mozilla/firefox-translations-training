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
from translations_parser.utils import parse_task_label

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
            if mode == ExperimentMode.SNAKEMAKE:
                # Snakemake experiments metrics are in the form `<importer><?_dataset>`
                importer, *dataset = metrics_file.stem.split("_", 1)
                dataset = dataset[0] if dataset else None
            else:
                # Taskcluster experiments metrics are in the form `<?augmentation_><dataset>`.
                # As importer is a required attribute, we publish the metric base on its file
                # name directly, making comparison with other type of publication impossible.
                importer = metrics_file.stem
                dataset = None
            metrics.append(Metric.from_file(metrics_file, importer=importer, dataset=dataset))

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
    existing_runs = []
    for index, (path, files) in enumerate(file_groups.items(), start=1):
        logger.info(f"Parsing folder {path.resolve()}")
        parents = path.parts[len(prefix) :]
        if len(parents) < 3:
            logger.warning(f"Skipping folder {path.resolve()}: Unexpected folder structure")
            continue
        project, group, *name = parents
        base_name = name[0]
        name = "_".join(name)

        if mode == ExperimentMode.TASKCLUSTER:
            if len(group) < 22:
                logger.error(
                    f"Skip folder {group} as it cannot contain a task group ID (too few caracters)."
                )
                continue
            suffix = f"_{group[-22:-17]}"
        else:
            # Defaults using the full experiment name as a suffix
            suffix = f"_{group}"

        try:
            name = parse_task_label(f"train-{name}").model
        except ValueError:
            logger.error(f"Invalid tag extracted from file @{path}: '{name}'")
            continue

        # Publish a run for each file inside that group
        for file in files:
            # Also publish metric files when available
            metrics_path = Path(
                "/".join([*prefix[:-1], "models", project, group, "evaluation", base_name])
            )
            metrics_dir = metrics_path if metrics_path.is_dir() else None
            if metrics_dir is None:
                logger.warning("Evaluation metrics files not found, skipping.")
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
                existing_runs.append(name)
            except Exception as e:
                logger.error(f"An exception occured parsing {file}: {e}")

        # Try to publish related log files to the group on a last run named "group_logs"
        if index == len(file_groups) or last_index and last_index != (project, group, suffix):
            last_project, last_group, last_suffix = (
                last_index
                if last_index
                # May occur when handling a single run
                else (project, group, suffix)
            )
            logger.info(
                f"Publishing '{last_project}/{last_group}' evaluation metrics and files (fake run 'group_logs')"
            )
            WandB.publish_group_logs(
                logs_parent_folder=prefix,
                project=last_project,
                group=last_group,
                suffix=last_suffix,
                existing_runs=existing_runs,
            )
            existing_runs = []

        last_index = (project, group, suffix)

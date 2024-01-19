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

# Keywords to split eval filenames into model and dataset
DATASET_KEYWORDS = ["flores", "mtdata", "sacrebleu"]


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
            metrics.append(Metric.from_file(model_name=name, metrics_file=metrics_file))

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
    prefix: str,
    project: str,
    group: str,
) -> None:
    """
    Publish all files within `logs_dir` to W&B artifacts for a specific group.
    A fake W&B run named `group_logs` is created to publish those artifacts among
    with all evaluation files (quantized + experiments).
    """
    logs_dir = Path("/".join([*prefix[:-1], "logs", project, group]))
    # Old experiments use `speed` directory for quantized metrics
    quantized_metrics = sorted(
        Path("/".join([*prefix, project, group, "evaluation", "speed"])).glob("*.metrics")
    )
    evaluation_metrics = sorted((logs_dir / "eval_").glob("eval*.log"))
    if not quantized_metrics:
        logger.warning(f"Quantized metrics not found for group {group}.")
    if not evaluation_metrics:
        logger.warning(f"Evaluation metrics not found for group {group}")

    # Add "quantized" metrics
    metrics = []
    for file in quantized_metrics:
        metrics.append(Metric.from_file("quantized", file))
    # Add experiment (runs) metrics
    for file in evaluation_metrics:
        model_name = file.stem.lstrip("eval_")
        dataset = ""
        # File names usually have a structure like "eval_<model_name>_<dataset>.log
        # model_name can be the name of a run, or the evaluation pre-trained model.
        for keyword in DATASET_KEYWORDS:
            if keyword in model_name:
                index = model_name.index(keyword)
                model_name, dataset = model_name[:index].strip("_"), model_name[index:]
                break
            else:
                continue
        if not dataset:
            logger.warning(
                f"No dataset could be extracted from file {file.name}. Please ensure DATASET_KEYWORDS is up to date."
            )
        with file.open("r") as f:
            lines = f.readlines()
        try:
            metrics.append(Metric.from_file(model_name, dataset, lines))
        except ValueError as e:
            logger.error(f"Could not parse metrics from {file.resolve()}: {e}")

    # Start publication
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
    if metrics:
        publisher.handle_metrics(metrics)

    # Publish logs directory content as artifacts
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
            logger.info(
                f"Publishing '{last_project}/{last_group}' evaluation metrics and files (fake run 'group_logs')"
            )
            publish_group_logs(prefix, last_project, last_group)
        last_index = (project, group)

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


def get_args():
    parser = argparse.ArgumentParser(description="Publish multiple experiments to Weight & Biases")
    parser.add_argument(
        "--directory",
        "-d",
        help="Path to the experiments directory.",
        type=Path,
        default=Path(Path(os.getcwd())),
    )
    return parser.parse_args()


def parse_experiment(logs_file, project, group, name, metrics_dir=None):
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


def publish_group_logs(project, group, logs_dir, metrics_dir):
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
    # Add "speed" metrics
    if metrics_dir.is_dir():
        metrics = []
        for metrics_file in metrics_dir.glob("*.metrics"):
            metrics.append(Metric.from_file(metrics_file))
    if metrics:
        publisher.handle_metrics(metrics)
    # Add logs dir content as artifacts
    if logs_dir.is_dir():
        artifact = wandb.Artifact(name=group, type="logs")
        artifact.add_dir(local_path=logs_dir)
        publisher.wandb.log_artifact(artifact)
        publisher.wandb.finish()
    publisher.wandb.finish()


def main():
    args = get_args()
    directory = args.directory
    # Ignore files with a different name than "train.log"
    file_groups = {
        path: list(files)
        for path, files in groupby(directory.glob("**/train.log"), lambda path: path.parent)
    }
    logger.info(f"Reading {len(file_groups)} train.log data")
    prefix = os.path.commonprefix([path.parts for path in file_groups])
    if "models" in prefix:
        prefix = prefix[: prefix.index("models") + 1]

    last_index = None
    for index, (path, files) in enumerate(file_groups.items(), start=1):
        logger.info(f"Parsing folder {path}")
        parents = path.parts[len(prefix) :]
        if len(parents) < 3:
            logger.warning(f"Skipping folder {path}: Unexpected folder structure")
            continue
        project, group, *name = parents
        base_name = name[0]
        name = "_".join(name)

        # Publish a run for each file inside that group
        for file in files:
            # Also publish metric files when available
            metrics_dir = Path("/".join([*prefix, project, group, "evaluation", base_name]))
            if not metrics_dir.is_dir():
                logger.warning("Evaluation metrics files not found, skipping.")
                metrics_dir = None
            try:
                parse_experiment(file, project, group, name, metrics_dir=metrics_dir)
            except Exception as e:
                logger.error(f"An exception occured parsing {file}: {e}")

        # Try to publish related log files to the group on a last run named "group_logs"
        if index == len(file_groups) or last_index and last_index != (project, group):
            last_project, last_group = last_index
            if (
                prefix
                and prefix[-1] == "models"
                and (
                    (
                        logs_dir := Path(
                            "/".join([*prefix[:-1], "logs", last_project, last_group])
                        )
                    ).is_dir()
                    or (
                        metrics_dir := Path(
                            "/".join([*prefix, last_project, last_group, "evaluation", "speed"])
                        )
                    ).is_dir()
                )
            ):
                logger.info(
                    f"Publishing '{last_project}' group '{last_group}' metrics and files to a last fake run 'group_logs'"
                )
                publish_group_logs(last_project, last_group, logs_dir, metrics_dir)
            else:
                logger.warning(
                    "No extra logs nor metrics found for this project, skipping 'group_logs' fake run."
                )
        last_index = (project, group)

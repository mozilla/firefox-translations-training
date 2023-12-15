import argparse
import logging
import os
from dataclasses import dataclass
from itertools import groupby
from pathlib import Path

import wandb

from translations_parser.parser import TrainingParser
from translations_parser.publishers import WandB

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class MetricEpoch:
    """
    A generic metric extracted from .metric files
    """

    up: int


class ExperimentsParser(TrainingParser):
    def __init__(self, *args, metrics_dir=None, **kwargs):
        self.metrics_dir = metrics_dir
        return super().__init__(*args, **kwargs)

    def run(self):
        """
        Add experiment metrics to the training data of the parser
        so they are also reported by the WandB publisher.
        """
        if not self.metrics_dir:
            return super().run()

        # Add Metrics to the published output based on the name of the file
        for metrics_file in self.metrics_dir.glob("*.metrics"):
            with metrics_file.open("r") as f:
                lines = f.readlines()
            up = 1
            for line in lines:
                # Ignore lines that does not contain a float value
                try:
                    value = float(line)
                except ValueError:
                    continue
                else:
                    metric = MetricEpoch(up=up)
                    setattr(
                        metric,
                        # Always prefix metrics to avoid names conflict
                        f"[metric] {metrics_file.stem}",
                        value,
                    )
                    self.training.append(metric)
                    up += 1
        return super().run()


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
    with logs_file.open("r") as f:
        lines = (line.strip() for line in f.readlines())
    parser = ExperimentsParser(
        lines,
        metrics_dir=metrics_dir,
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


def publish_group_logs(project, group, logs_dir):
    run = wandb.init(
        project=project,
        group=group,
        name="group_logs",
    )
    artifact = wandb.Artifact(name=group, type="logs")
    artifact.add_dir(local_path=logs_dir)
    run.log_artifact(artifact)
    run.finish()


def main():
    args = get_args()
    directory = args.directory
    # Ignore files with a different name than "train.log"
    file_groups = {
        path: list(files) for path, files in groupby(directory.glob("**/train.log"), lambda path: path.parent)
    }
    logger.info(f"Reading {len(file_groups)} train.log data")
    prefix = os.path.commonprefix([path.parts for path in file_groups])

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

        # Try to publish related log files to the group on a last run named "group_logs"
        if index == len(file_groups) or last_index and last_index != (project, group):
            last_project, last_group = last_index
            logger.info(f"Publishing related files for project {last_project} group {last_group}")
            if (
                prefix
                and prefix[-1] == "models"
                and (path := Path("/".join([*prefix[:-1], "logs", last_project, last_group]))).is_dir()
            ):
                publish_group_logs(last_project, last_group, path)
            else:
                logger.warning("Logs folder not found, skipping.")
        last_index = (project, group)

        # Publish a run for each file inside that group
        for index, file in enumerate(files, start=1):
            # Also publish metric files when available
            metrics_dir = Path("/".join([*prefix, project, group, "evaluation", base_name]))
            if not metrics_dir.is_dir():
                logger.warning("Evaluation metrics files not found, skipping.")
                metrics_dir = None
            try:
                parse_experiment(file, project, group, name, metrics_dir=metrics_dir)
            except Exception as e:
                logger.error(f"An exception occured parsing {file}: {e}")

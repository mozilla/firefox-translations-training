import csv
import logging
from abc import ABC
from pathlib import Path

import wandb

from translations_parser.data import TrainingEpoch, TrainingLog, ValidationEpoch

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


class Publisher(ABC):
    """
    Generic mixin to publish parsed data.
    Either the `handle_*` methods can be overriden for real time publication or
    the `publish` method with all results (including run date, configuration…).
    """

    def open(self, parser) -> None:
        ...

    def handle_training(self, training: TrainingEpoch) -> None:
        ...

    def handle_validation(self, validation: ValidationEpoch) -> None:
        ...

    def publish(self, log: TrainingLog) -> None:
        ...

    def close(self) -> None:
        ...


class CSVExport(Publisher):
    def __init__(self, output_dir):
        assert output_dir.is_dir(), "Output must be a valid directory"
        self.output_dir = output_dir

    def write_data(self, output, entries, dataclass):
        if not entries:
            logger.warning(f"No {dataclass.__name__} entry, skipping.")
        with open(output, "w") as f:
            writer = csv.DictWriter(f, fieldnames=dataclass.__annotations__)
            writer.writeheader()
            for entry in entries:
                writer.writerow(vars(entry))

    def publish(self, training_log):
        training_output = self.output_dir / "training.csv"
        if training_output.exists():
            logger.warning(f"Training output file {training_output} exists, skipping.")
        else:
            self.write_data(training_output, training_log.training, TrainingEpoch)

        validation_output = self.output_dir / "validation.csv"
        if validation_output.exists():
            logger.warning(f"Validation output file {validation_output} exists, skipping.")
        else:
            self.write_data(validation_output, training_log.validation, ValidationEpoch)


class WandB(Publisher):
    def __init__(self, project, artifacts=None, artifacts_name="logs", **extra_kwargs):
        self.project = project
        # Optional path to a directory containing training artifacts
        self.artifacts = artifacts
        self.artifacts_name = artifacts_name
        self.extra_kwargs = extra_kwargs
        self.parser = None

    def open(self, parser):
        self.parser = parser
        config = parser.config
        config.update(self.extra_kwargs.pop("config", {}))
        # Start a W&B run
        self.wandb = wandb.init(
            project=self.project,
            config=config,
            **self.extra_kwargs,
        )

    def generic_log(self, data):
        epoch = vars(data)
        step = epoch.pop("up")
        for key, val in epoch.items():
            wandb.log(step=step, data={key: val})

    def handle_training(self, training):
        self.generic_log(training)

    def handle_validation(self, validation):
        self.generic_log(validation)

    def close(self):
        # Store runtime logs as the main log artifact
        # This will be overwritten in case an unhandled exception occurs
        with (Path(self.wandb.dir) / "output.log").open("w") as f:
            f.write(self.parser.logs_str)

        # Publish artifacts
        if self.artifacts:
            artifact = wandb.Artifact(name=self.artifacts_name, type=self.artifacts_name)
            artifact.add_dir(local_path=self.artifacts)
            self.wandb.log_artifact(artifact)

        self.wandb.finish()

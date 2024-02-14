import csv
import logging
from abc import ABC
from collections import defaultdict
from pathlib import Path
from typing import Sequence

import wandb
from translations_parser.data import Metric, TrainingEpoch, TrainingLog, ValidationEpoch
from translations_parser.utils import extract_dataset_from_tag

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


class Publisher(ABC):
    """
    Abstract class used to publish parsed data.

    Either the `handle_*` methods can be overriden for real time
    publication (introduced later on) or the `publish` method
    with all results (including parser run date, configuration…).
    """

    def open(self, parser) -> None:
        ...

    def handle_training(self, training: TrainingEpoch) -> None:
        ...

    def handle_validation(self, validation: ValidationEpoch) -> None:
        ...

    def handle_metrics(self, metrics: Sequence[Metric]) -> None:
        ...

    def publish(self, log: TrainingLog) -> None:
        ...

    def close(self) -> None:
        ...


class CSVExport(Publisher):
    def __init__(self, output_dir: Path) -> None:
        if not output_dir.is_dir():
            raise ValueError("Output must be a valid directory for the CSV export")
        self.output_dir = output_dir

    def write_data(
        self, output: Path, entries: Sequence[TrainingEpoch | ValidationEpoch], dataclass: type
    ) -> None:
        if not entries:
            logger.warning(f"No {dataclass.__name__} entry, skipping.")
        with open(output, "w") as f:
            writer = csv.DictWriter(f, fieldnames=dataclass.__annotations__)
            writer.writeheader()
            for entry in entries:
                writer.writerow(vars(entry))

    def publish(self, training_log: TrainingLog) -> None:
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
    def __init__(
        self,
        project: str,
        # Optional path to a directory containing training artifacts
        artifacts: Path | None = None,
        artifacts_name: str = "logs",
        **extra_kwargs,
    ):
        from translations_parser.parser import TrainingParser

        self.project = project
        self.artifacts = artifacts
        self.artifacts_name = artifacts_name
        self.extra_kwargs = extra_kwargs
        self.parser: TrainingParser | None = None
        self.wandb: wandb.sdk.wandb_run.Run | wandb.sdk.lib.disabled.RunDisabled | None = None

    def open(self, parser) -> None:
        if parser is None or self.parser is not None:
            return
        self.parser = parser
        config = parser.config
        config.update(self.extra_kwargs.pop("config", {}))
        # Start a W&B run
        try:
            self.wandb = wandb.init(
                project=self.project,
                config=config,
                **self.extra_kwargs,
            )
        except Exception as e:
            logger.error(f"WandB client could not be initialized: {e}. No data will be published.")

    def generic_log(self, data: TrainingEpoch | ValidationEpoch) -> None:
        if self.wandb is None:
            return
        epoch = vars(data)
        step = epoch.pop("up")
        for key, val in epoch.items():
            self.wandb.log(step=step, data={key: val})

    def handle_training(self, training: TrainingEpoch) -> None:
        self.generic_log(training)

    def handle_validation(self, validation: ValidationEpoch) -> None:
        self.generic_log(validation)

    def handle_metrics(self, metrics: Sequence[Metric]) -> None:
        if self.wandb is None:
            return
        for metric in metrics:
            # Publish a bar chart (a table with values will also be available from W&B)
            self.wandb.log(
                {
                    metric.dataset: wandb.plot.bar(
                        wandb.Table(
                            columns=["Metric", "Value"],
                            data=[[key, getattr(metric, key)] for key in ("bleu_detok", "chrf")],
                        ),
                        "Metric",
                        "Value",
                        title=metric.dataset.capitalize(),
                    )
                }
            )

    def close(self) -> None:
        if self.wandb is None or self.parser is None:
            return
        # Store runtime logs as the main log artifact
        # This will be overwritten in case an unhandled exception occurs
        with (Path(self.wandb.dir) / "output.log").open("w") as f:
            f.write(self.parser.logs_str)

        # Publish artifacts
        if self.artifacts:
            artifact = wandb.Artifact(name=self.artifacts_name, type=self.artifacts_name)
            artifact.add_dir(local_path=str(self.artifacts.resolve()))
            self.wandb.log_artifact(artifact)

        self.wandb.finish()

    @classmethod
    def publish_group_logs(
        cls,
        logs_parent_folder: str,
        project: str,
        group: str,
        existing_runs: list[str] | None = None,
    ) -> None:
        """
        Publish files within `logs_dir` to W&B artifacts for a specific group.
        A fake W&B run named `group_logs` is created to publish those artifacts
        among with all evaluation files (quantized + experiments).
        If existing run is set, runs found not specified in this list will also
        be published to W&B.
        """
        from translations_parser.parser import TrainingParser

        logs_dir = Path("/".join([*logs_parent_folder[:-1], "logs", project, group]))
        # Old experiments use `speed` directory for quantized metrics
        quantized_metrics = sorted(
            Path("/".join([*logs_parent_folder, project, group, "evaluation", "speed"])).glob(
                "*.metrics"
            )
        )
        evaluation_metrics = sorted((logs_dir / "eval").glob("eval*.log"))
        if quantized_metrics:
            logger.info(f"Found {len(quantized_metrics)} quantized metrics")
        else:
            logger.warning(f"No quantized metric found for group {group}, skipping")
        if evaluation_metrics:
            logger.info(f"Found {len(evaluation_metrics)} evaluation metrics")
        else:
            logger.warning(f"No evaluation metrics not found for group {group}, skipping")

        # Store metrics by run name
        metrics = defaultdict(list)
        # Add "quantized" metrics
        for file in quantized_metrics:
            metrics["quantized"].append(Metric.from_file(file, dataset=file.stem))
        # Add experiment (runs) metrics
        for file in evaluation_metrics:
            model_name, dataset, aug = extract_dataset_from_tag(file.stem)
            with file.open("r") as f:
                lines = f.readlines()
            try:
                metrics[model_name].append(Metric.from_tc_context(dataset, lines))
            except ValueError as e:
                logger.error(f"Could not parse metrics from {file.resolve()}: {e}")

        # Publish missing runs (runs without training data)
        missing_run_metrics = {}
        if existing_runs is not None:
            missing_run_metrics = {
                name: metrics for name, metrics in metrics.items() if name not in existing_runs
            }

        for model_name, model_metrics in missing_run_metrics.items():
            logger.info(f"Creating missing run {model_name} with associated metrics")
            publisher = cls(project=project, name=model_name, group=group)
            publisher.open(TrainingParser(logs_iter=iter([]), publishers=[]))
            publisher.handle_metrics(model_metrics)
            publisher.close()

        # Start publication of `group_logs` fake run
        publisher = cls(
            project=project,
            group=group,
            name="group_logs",
        )
        publisher.wandb = wandb.init(
            project=project,
            group=group,
            name="group_logs",
        )

        # Publish all evaluation metrics to a table
        if metrics:
            table = wandb.Table(
                columns=["Group", "Model", "Dataset", "BLEU", "chrF"],
                data=[
                    [group, run_name, metric.dataset, metric.bleu_detok, metric.chrf]
                    for run_name, run_metrics in metrics.items()
                    for metric in run_metrics
                ],
            )
            publisher.wandb.log({"metrics": table})

        # Publish logs directory content as artifacts
        if logs_dir.is_dir():
            artifact = wandb.Artifact(name=group, type="logs")
            artifact.add_dir(local_path=str(logs_dir.resolve()))
            publisher.wandb.log_artifact(artifact)
        publisher.wandb.finish()

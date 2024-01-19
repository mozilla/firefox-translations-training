import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Sequence

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

METRIC_LOG_RE = re.compile(
    r"|".join(
        [
            r"\+ tee .+\.metrics",
            r"\+ tee .+\.en",
            r"\+ sacrebleu .+",
            r"\+ .+\/marian-decoder .+",
            # Ignore potential comments
            r"^sacreBLEU:",
        ]
    )
)


@dataclass
class TrainingEpoch:
    epoch: int
    up: int
    sen: int
    cost: float
    time: float
    rate: float
    gnorm: float


@dataclass
class ValidationEpoch:
    epoch: int
    up: int
    chrf: float
    ce_mean_words: float
    bleu_detok: float


@dataclass
class Metric:
    """Data extracted from a `.metrics` file"""

    # Evaluation identifiers
    model_name: str
    dataset: str
    augmentation: str | None
    # Scores
    chrf: float
    bleu_detok: float

    @classmethod
    def from_file(cls, model_name: str, metrics_file: Path):
        logger.debug(f"Reading metrics file {metrics_file.name}")
        values = []
        try:
            with metrics_file.open("r") as f:
                lines = f.readlines()
            for line in lines:
                try:
                    values.append(float(line))
                except ValueError:
                    continue
            assert len(values) == 2, "file must contain exactly 2 float values"
        except Exception as e:
            raise ValueError(f"Metrics file could not be parsed: {e}")
        bleu_detok, chrf = values
        return cls(
            model_name=model_name,
            dataset=metrics_file.stem,
            augmentation=None,
            chrf=chrf,
            bleu_detok=bleu_detok,
        )

    @classmethod
    def from_tc_context(cls, model_name: str, dataset: str, lines: Sequence[str]):
        """
        Try reading a metric from Taskcluster logs, looking for two
        successive floats after a line maching METRIC_LOG_RE.
        """
        for index, line in enumerate(lines):
            if not METRIC_LOG_RE.match(line):
                continue
            try:
                values = [float(val) for val in lines[index + 1 : index + 3]]
            except ValueError:
                continue
            if len(values) != 2:
                continue
            bleu_detok, chrf = values
            return cls(
                model_name=model_name,
                dataset=dataset,
                augmentation=None,
                chrf=chrf,
                bleu_detok=bleu_detok,
            )
        raise ValueError("Metrics logs could not be parsed")


@dataclass
class TrainingLog:
    """Results from the parsing of a training log file"""

    # Runtime configuration
    configuration: dict
    training: List[TrainingEpoch]
    validation: List[ValidationEpoch]
    # Dict of log lines indexed by their header (e.g. marian, data, memory)
    logs: dict
    run_date: datetime | None

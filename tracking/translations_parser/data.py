import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


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
    """A simple key:value metric extracted from `.metrics` files"""

    name: str
    chrf: float
    bleu_detok: float

    @classmethod
    def from_file(cls, metrics_file: Path):
        logger.info(f"Reading metrics file {metrics_file.name}")
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
        chrf, bleu_detok = values
        return cls(name=metrics_file.stem, chrf=chrf, bleu_detok=bleu_detok)


@dataclass
class TrainingLog:
    """Results from the parsing of a training log file"""

    # Runtime configuration
    configuration: dict
    training: List[TrainingEpoch]
    validation: List[ValidationEpoch]
    # Dict of log lines indexed by their header (e.g. marian, data, memory)
    logs: dict
    run_date: datetime

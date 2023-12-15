from dataclasses import dataclass
from datetime import datetime
from typing import List


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
class TrainingLog:
    """Results from the parsing of a training log file"""

    # Runtime configuration
    configuration: dict
    training: List[TrainingEpoch]
    validation: List[ValidationEpoch]
    # Dict of log lines indexed by their header (e.g. marian, data, memory)
    logs: dict
    run_date: datetime

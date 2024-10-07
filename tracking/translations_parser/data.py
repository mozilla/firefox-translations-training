import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Sequence

from translations_parser.utils import parse_task_label

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
TC_PREFIX_RE = re.compile(r"^\[task [0-9\-TZ:\.]+\]")


@dataclass
class TrainingEpoch:
    epoch: int
    up: int
    sen: int
    cost: float
    time: float
    rate: float  # Words per second
    gnorm: float
    learning_rate: float | None = None  # Optional


@dataclass
class ValidationEpoch:
    epoch: int
    up: int
    chrf: float
    ce_mean_words: float
    bleu_detok: float
    perplexity: float = None  # optional
    # Optional stalled validation metrics
    chrf_stalled: int | None = None
    ce_mean_words_stalled: int | None = None
    bleu_detok_stalled: int | None = None
    perplexity_stalled: float = None  # optional


@dataclass
class Metric:
    """Data extracted from a `.metrics` file"""

    # Evaluation identifiers
    importer: str
    dataset: str
    augmentation: str | None
    # Scores
    chrf: float
    bleu_detok: float
    comet: float | None = None  # optional

    @classmethod
    def from_file(
        cls,
        metrics_file: Path,
        importer: str | None = None,
        dataset: str | None = None,
        augmentation: str | None = None,
    ):
        """
        Instanciate a Metric from a `.metrics` file.
        In case no dataset is set, detects it from the filename.
        """
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
            assert len(values) in (2, 3), "file must contain 2 or 3 lines with a float value"
        except Exception as e:
            raise ValueError(f"Metrics file could not be parsed: {e}")
        if len(values) == 2:
            bleu_detok, chrf = values
            comet = None
        if len(values) == 3:
            bleu_detok, chrf, comet = values
        if importer is None:
            _, importer, dataset, augmentation = parse_task_label(metrics_file.stem)

        # Multiply metric by 100 to match other metrics percentage style
        if comet is not None:
            comet *= 100

        return cls(
            importer=importer,
            dataset=dataset,
            augmentation=augmentation,
            chrf=chrf,
            bleu_detok=bleu_detok,
            comet=comet,
        )

    @classmethod
    def from_tc_context(
        cls, importer: str, dataset: str, lines: Sequence[str], augmentation: str | None = None
    ):
        """
        Try reading a metric from Taskcluster logs, looking for two
        successive floats after a line maching METRIC_LOG_RE.
        """
        for index, line in enumerate(lines):
            # Remove eventual Taskcluster prefix
            clean_line = TC_PREFIX_RE.sub("", line).strip()
            if not METRIC_LOG_RE.match(clean_line):
                continue
            try:
                values = [float(TC_PREFIX_RE.sub("", val)) for val in lines[index + 1 : index + 3]]
            except ValueError:
                continue
            if len(values) != 2:
                continue
            bleu_detok, chrf = values
            return cls(
                importer=importer,
                dataset=dataset,
                augmentation=augmentation,
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
    logs: List[str]
    run_date: datetime | None

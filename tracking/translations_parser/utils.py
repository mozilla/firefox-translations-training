import logging
import re
from collections.abc import Sequence
from datetime import datetime
from typing import NamedTuple, Optional

logger = logging.getLogger(__name__)

# Keywords used to split eval filenames into model and dataset
DATASET_KEYWORDS = ["flores", "mtdata", "sacrebleu"]

# Tags usually ends with project (e.g. `en-nl` or `eng-nld`)
TAG_PROJECT_SUFFIX_REGEX = re.compile(r"((-\w{2}){2}|(-\w{3}){2})$")


# This regex needs to work on historic runs as well as the current tasks.
TRAIN_LABEL_REGEX = re.compile(
    r"^"
    r"train-"
    #
    # Capture what model is being run, for instance:
    #   train-teacher-ru-en-1
    #         ^^^^^^^
    r"(?P<model>"
    r"(finetuned-student|finetune-student|student-finetuned|teacher-ensemble|teacher|teacher-base|teacher-finetuned"
    r"|finetune-teacher|teacher-all|teacher-parallel|student|quantized|backwards|backward)"
    r")"
    #
    # Capture some legacy numeric suffixes.
    r"(-?(?P<suffix>\d+))?"
    r"[_-]?"
    #
    # Match the languages.
    #   train-teacher-ru-en-1
    #                 ^^ ^^
    r"(?P<lang>[a-z]{2}-[a-z]{2})?"
    r"-?"
    #
    # Match the task chunking, for instance:
    #   train-teacher-ru-en-1
    #                       ^
    # Legacy pattern:
    #   train-teacher-ru-en-1/3
    #                       ^
    r"-?((?P<task_suffix>\d+)((\/|_)\d+)?)?"
    #
    r"$"
)
EVAL_REGEX = re.compile(
    r"^"
    # Match evaluate steps.
    r"(evaluate|eval)[-_]"
    #
    # Capture what model is being run, for instance:
    #   evaluate-student-sacrebleu-wmt19-lt-en
    #            ^^^^^^^
    r"(?P<model>"
    r"(finetuned-student|finetune-student|student-finetuned|teacher-ensemble|teacher|teacher-base|teacher-finetuned"
    r"|finetune-teacher|teacher-all|teacher-parallel|student|quantized|backwards|backward)"
    r")"
    #
    # Capture some legacy numeric suffixes.
    r"(-?(?P<suffix>\d+))?"
    r"[_-]"
    #
    # Capture which importer is being used.
    #   evaluate-teacher-flores-flores_aug-title_devtest-lt-en-1_2
    #                    ^^^^^^
    r"(?P<importer>flores|mtdata|sacrebleu|url)"
    r"(?P<extra_importer>-flores|-mtdata|-sacrebleu)?"
    r"[_-]"
    #
    # Capture any augmentations
    #   evaluate-teacher-flores-flores_aug-title_devtest-lt-en-1_2
    #                                  ^^^^^^^^^
    r"(?P<aug>aug-[^_]+)?"
    #
    # Capture the dataset.
    #   evaluate-quantized-mtdata_aug-mix_Neulab-tedtalks_eng-lit-lt-en
    #                                     ^^^^^^^^^^^^^^^^^^^^^^^
    r"_?(?P<dataset>[-\w\d_]*?(-[a-z]{3}-[a-z]{3})?)?"
    r"-?(?P<lang>[a-z]{2}-[a-z]{2})?"
    #
    # Match the task chunking, for instance:
    #   evaluate-teacher-flores-flores_dev-en-ca-1/2
    #                                            ^
    #   evaluate-teacher-flores-flores_aug-title_devtest-lt-en-1_2
    #                                                          ^
    r"-?((?P<task_suffix>\d+)(\/|_)\d+)?"
    #
    r"$"
)
MULTIPLE_TRAIN_SUFFIX = re.compile(r"(-\d+)/\d+$")


class ParsedTaskLabel(NamedTuple):
    model: str
    importer: Optional[str]
    dataset: Optional[str]
    augmentation: Optional[str]


def parse_task_label(task_label: str) -> ParsedTaskLabel:
    """
    Parse details out of train-* and evaluate-* task labels.
    """
    # First try to parse a simple training label
    match = TRAIN_LABEL_REGEX.match(task_label)
    if match is None:
        # Else try to parse an evaluation label with importer, dataset and auugmentation
        match = EVAL_REGEX.match(task_label)
    if not match:
        raise ValueError(task_label)
    groups = match.groupdict()
    model = groups["model"]
    suffix = groups.get("suffix") or groups.get("task_suffix")
    if not suffix and model == "teacher":
        # Keep the index on teacher runs for compatibility with legacy models
        # https://github.com/mozilla/firefox-translations-training/issues/573
        suffix = "1"
    if suffix:
        model = f"{model}-{suffix}"
    return ParsedTaskLabel(model, groups.get("importer"), groups.get("dataset"), groups.get("aug"))


def taskcluster_log_filter(headers: Sequence[Sequence[str]]) -> bool:
    """
    Check TC log contain a valid task header i.e. ('task', <timestamp>)
    """
    for values in headers:
        if not values or len(values) != 2:
            continue
        base, timestamp = values
        if base != "task":
            continue
        try:
            datetime.fromisoformat(timestamp.rstrip("Z"))
            return True
        except ValueError:
            continue
    return False


def build_task_name(task: dict):
    """
    Build a simpler task name using a Taskcluster task payload (without status)
    """
    prefix = task["tags"]["kind"].split("-")[0]
    label = parse_task_label(task["tags"]["label"])
    return prefix, label.model

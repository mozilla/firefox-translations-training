import logging
import re
from collections.abc import Sequence
from datetime import datetime

logger = logging.getLogger(__name__)

# Keywords used to split eval filenames into model and dataset
DATASET_KEYWORDS = ["flores", "mtdata", "sacrebleu"]

# Tags usually ends with project (e.g. `en-nl` or `eng-nld`)
TAG_PROJECT_SUFFIX_REGEX = re.compile(r"((-\w{2}){2}|(-\w{3}){2})$")


TRAIN_LABEL_REGEX = re.compile(
    r"^"
    r"train-"
    r"(?P<model>"
    r"(finetuned-student|finetune-student|student-finetuned|teacher-ensemble|teacher|teacher-base|teacher-finetuned"
    r"|finetune-teacher|teacher-all|teacher-parallel|student|quantized|backwards|backward)"
    r")"
    r"(-?(?P<suffix>\d+))?"
    r"[_-]?"
    r"(?P<lang>[a-z]{2}-[a-z]{2})?"
    r"-?"
    r"-?((?P<task_suffix>\d+)(\/|_)\d+)?"
    r"$"
)
EVAL_REGEX = re.compile(
    r"^"
    r"(evaluate|eval)[-_]"
    r"(?P<model>"
    r"(finetuned-student|finetune-student|student-finetuned|teacher-ensemble|teacher|teacher-base|teacher-finetuned"
    r"|finetune-teacher|teacher-all|teacher-parallel|student|quantized|backwards|backward)"
    r")"
    r"(-?(?P<suffix>\d+))?"
    r"[_-]"
    r"(?P<importer>flores|mtdata|sacrebleu)"
    r"(?P<extra_importer>-flores|-mtdata|-sacrebleu)?"
    r"[_-]"
    r"(?P<aug>aug-[^_]+)?"
    r"_?(?P<dataset>[-\w_]*?(-[a-z]{3}-[a-z]{3})?)?"
    r"-?(?P<lang>[a-z]{2}-[a-z]{2})?"
    r"-?((?P<task_suffix>\d+)(\/|_)\d+)?"
    r"$"
)
MULTIPLE_TRAIN_SUFFIX = re.compile(r"(-\d+)/\d+$")


def parse_tag(tag, sep="_"):
    # First try to parse a simple training label
    match = TRAIN_LABEL_REGEX.match(tag)
    if match is None:
        # Else try to parse an evaluation label with importer, dataset and auugmentation
        match = EVAL_REGEX.match(tag)
    if not match:
        raise ValueError(tag)
    groups = match.groupdict()
    model = groups["model"]
    suffix = groups.get("suffix") or groups.get("task_suffix")
    if not suffix and model == "teacher":
        # Keep the index on teacher runs for compatibility with legacy models
        # https://github.com/mozilla/firefox-translations-training/issues/573
        suffix = "1"
    if suffix:
        model = f"{model}-{suffix}"
    return model, groups.get("importer"), groups.get("dataset"), groups.get("aug")


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
    model, *_ = parse_tag(task["tags"]["label"])
    return prefix, model

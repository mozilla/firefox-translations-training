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
    r"(finetuned-student|student-finetuned|teacher-ensemble|teacher|teacher-base|teacher-finetuned"
    r"|student|quantized|backwards|backward)"
    r"(-?\d+)?"
    r")"
    r"[_-]"
    r"(?P<lang>[a-z]{2}-[a-z]{2})"
    r"-?"
    r"-?(?P<suffix>[\d_\/]+)?$"
    r"$"
)
EVAL_REGEX = re.compile(
    r"^"
    r"(evaluate|eval)[-_]"
    r"(?P<model>"
    r"(finetuned-student|student-finetuned|teacher-ensemble|teacher|teacher-base|teacher-finetuned"
    r"|student|quantized|backwards|backward)"
    r"(-?\d+)?"
    r")"
    r"[_-]"
    r"(?P<importer>flores|mtdata|sacrebleu)"
    r"(?P<extra_importer>-flores|-mtdata|-sacrebleu)?"
    r"[_-]"
    r"(?P<aug>aug-[^_]+)?"
    r"_?(?P<dataset>[-\w_]*?(-[a-z]{3}-[a-z]{3})?)?"
    r"-?(?P<lang>[a-z]{2}-[a-z]{2})?"
    r"-?(?P<suffix>[\d_\/]+)?$"
    r"$"
)
MULTIPLE_TRAIN_SUFFIX = re.compile(r"(-\d+)/\d+$")


def parse_tag(tag, sep="_"):
    # First try to parse a simple training label
    match = TRAIN_LABEL_REGEX.match(tag)
    if match is not None:
        return match.groupdict()["model"], None, None, None
    # Else try to parse an evaluation label with importer, dataset and auugmentation
    match = EVAL_REGEX.match(tag)
    if not match:
        raise ValueError(tag)
    groups = match.groupdict()
    return groups["model"], groups["importer"], groups["dataset"], groups["aug"]


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
    name = task["tags"]["kind"]
    prefix = name.split("-")[0]
    if prefix == "train":
        # Remove "train-" prefix from training task only to avoid duplicates
        name = name[6:]

    # Teacher training may run multiple times (e.g. "-1/2" prefix)
    suffix = ""
    label = task["tags"].get("label")
    if label and (re_match := MULTIPLE_TRAIN_SUFFIX.search(label)):
        (suffix,) = re_match.groups()

    # Final name uses the cleaned suffix
    return prefix, name + suffix

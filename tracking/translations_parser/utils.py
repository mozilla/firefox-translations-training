import logging
import re
from collections.abc import Sequence
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Keywords used to split eval filenames into model and dataset
DATASET_KEYWORDS = ["flores", "mtdata", "sacrebleu"]

# Tags usually ends with project (e.g. `en-nl` or `eng-nld`)
TAG_PROJECT_SUFFIX_REGEX = re.compile(r"((-\w{2}){2}|(-\w{3}){2})$")


def extract_dataset_from_tag(tag, sep="_") -> tuple[str, str, str | None]:
    """
    Experiment tag usually has a structure like "<prefix>_<model_name>_<dataset>_<?augmentation>_<project>"
    This function removes the prefix and suffix, and try to split model, dataset and optional augmentation.
    """
    prefix, *name = tag.split(sep, 1)
    if len(name) != 1:
        raise ValueError(f"Tag could not be parsed: '{tag}'.")
    model_name = name[0]
    # Eventually remove suffix
    name = TAG_PROJECT_SUFFIX_REGEX.sub("", model_name)
    dataset = ""
    aug = None
    for keyword in DATASET_KEYWORDS:
        if keyword in model_name:
            index = model_name.index(keyword)
            model_name, dataset = model_name[:index].rstrip(sep), model_name[index:]
            break
        else:
            continue
    if dataset:
        # Look for augmentation information in the second part of the tag (dataset)
        if "aug" in model_name:
            index = model_name.index("aug")
            dataset, aug = dataset[:index].rstrip(sep), dataset[index:]
    else:
        logger.warning(
            f"No dataset could be extracted from {tag}."
            " Please ensure utils.DATASET_KEYWORDS is up to date."
        )
    return model_name, dataset, aug


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

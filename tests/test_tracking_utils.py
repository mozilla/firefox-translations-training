import pytest
from fixtures import get_full_taskgraph

from tracking.translations_parser.utils import ParsedTaskLabel, build_task_name, parse_task_label


@pytest.mark.parametrize(
    "task_label, parsed_values",
    [
        (
            "evaluate-teacher-flores-flores_aug-title_devtest-lt-en-1_2",
            ("teacher-1", "flores", "devtest", "aug-title"),
        ),
        (
            "evaluate-quantized-mtdata_aug-mix_Neulab-tedtalks_eng-lit-lt-en",
            ("quantized", "mtdata", "Neulab-tedtalks_eng-lit", "aug-mix"),
        ),
        (
            "evaluate-finetune-teacher-sacrebleu-wmt19-lt-en-2_2",
            ("finetune-teacher-2", "sacrebleu", "wmt19", None),
        ),
        (
            "evaluate-student-sacrebleu-wmt19-lt-en",
            ("student", "sacrebleu", "wmt19", None),
        ),
        (
            "train-student-en-hu",
            ("student", None, None, None),
        ),
        (
            "eval_teacher-ensemble_mtdata_Neulab-tedtalks_test-1-eng-nld",
            ("teacher-ensemble", "mtdata", "Neulab-tedtalks_test-1-eng-nld", None),
        ),
        (
            "eval_student-finetuned_flores_devtest",
            ("student-finetuned", "flores", "devtest", None),
        ),
        (
            "eval_teacher-base0_flores_devtest",
            ("teacher-base-0", "flores", "devtest", None),
        ),
        (
            "train-backwards-en-ca",
            ("backwards", None, None, None),
        ),
        (
            "evaluate-teacher-flores-flores_dev-en-ca-1/2",
            ("teacher-1", "flores", "dev", None),
        ),
        (
            "train-teacher-ensemble",
            ("teacher-ensemble", None, None, None),
        ),
        (
            "evaluate-teacher-flores-flores_dev-en-ca",
            ("teacher-1", "flores", "dev", None),
        ),
        (
            "train-finetune-student-ru-en",
            ("finetune-student", None, None, None),
        ),
        (
            "train-teacher-ru-en-1",
            ("teacher-1", None, None, None),
        ),
        (
            "evaluate-backward-url-gcp_pytest-dataset_a0017e-en-ru",
            ("backward", "url", "gcp_pytest-dataset_a0017e", None),
        ),
    ],
)
def test_parse_task_label(task_label, parsed_values):
    assert parse_task_label(task_label) == ParsedTaskLabel(*parsed_values)


def test_parse_labels_on_full_taskgraph():
    """Ensure that all the taskgraph task labels parse."""
    for task in get_full_taskgraph():
        if not task.startswith("train-") and not task.startswith("evaluate-"):
            continue
        if task.startswith("train-vocab"):
            continue
        print(task)
        # This throws when it fails to parse.
        parse_task_label(task)


@pytest.mark.parametrize(
    "task_tags, values",
    [
        (
            {
                "os": "linux",
                "kind": "train-student",
                "label": "train-student-lt-en",
            },
            ("train", "student"),
        ),
        (
            {
                "os": "linux",
                "kind": "evaluate",
                "label": "evaluate-teacher-sacrebleu-sacrebleu_aug-upper_wmt19-lt-en-2/2",
            },
            ("evaluate", "teacher-2"),
        ),
    ],
)
def test_build_task_name(task_tags, values):
    task = {"tags": task_tags}
    assert build_task_name(task) == values

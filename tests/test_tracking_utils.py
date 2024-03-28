import pytest

from tracking.translations_parser.utils import parse_tag


@pytest.mark.parametrize(
    "example, parsed_values",
    [
        (
            "evaluate-teacher-flores-flores_aug-title_devtest-lt-en-1_2",
            ("teacher", "flores", "devtest", "aug-title"),
        ),
        (
            "evaluate-quantized-mtdata_aug-mix_Neulab-tedtalks_eng-lit-lt-en-1_2",
            ("quantized", "mtdata", "Neulab-tedtalks_eng-lit", "aug-mix"),
        ),
        (
            "evaluate-finetuned-student-sacrebleu-wmt19-lt-en",
            ("finetuned-student", "sacrebleu", "wmt19", None),
        ),
        (
            "evaluate-student-2-sacrebleu-wmt19-lt-en",
            ("student-2", "sacrebleu", "wmt19", None),
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
            ("teacher-base0", "flores", "devtest", None),
        ),
        (
            "train-backwards-en-ca",
            ("backwards", None, None, None),
        ),
        (
            "evaluate-teacher-flores-flores_dev-en-ca-1/2",
            ("teacher", "flores", "dev", None),
        ),
    ],
)
def test_parse_tag(example, parsed_values):
    assert parse_tag(example) == parsed_values

from tracking.translations_parser.utils import parse_tag_regex


def test_parse_tag_dup_importer():
    assert parse_tag_regex("evaluate-teacher-flores-flores_aug-title_devtest-lt-en-1_2") == (
        "teacher",
        "flores",
        "devtest",
        "aug-title",
    )


def test_parse_tag_extra_lang():
    assert parse_tag_regex(
        "evaluate-teacher-mtdata_aug-mix_Neulab-tedtalks_eng-lit-lt-en-1_2"
    ) == ("teacher", "mtdata", "Neulab-tedtalks_eng-lit", "aug-mix")


def test_parse_tag_null_aug():
    assert parse_tag_regex("evaluate-finetuned-student-sacrebleu-wmt19-lt-en") == (
        "finetuned-student",
        "sacrebleu",
        "wmt19",
        None,
    )


def test_parse_tag_complex_model():
    assert parse_tag_regex("evaluate-student-2-sacrebleu-wmt19-lt-en") == (
        "student-2",
        "sacrebleu",
        "wmt19",
        None,
    )

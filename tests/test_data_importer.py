import os

import pytest
import zstandard as zstd
from fixtures import DataDir, en_sample, get_mocked_downloads, ru_sample

SRC = "ru"
TRG = "en"
ARTIFACT_EXT = "zst"
COMPRESSION_CMD = "zstd"
CURRENT_FOLDER = os.path.dirname(os.path.abspath(__file__))

os.environ["ARTIFACT_EXT"] = ARTIFACT_EXT
os.environ["COMPRESSION_CMD"] = COMPRESSION_CMD
os.environ["SRC"] = SRC
os.environ["TRG"] = TRG


from pipeline.data.dataset_importer import run_import

# the augmentation is probabilistic, here is a range for 0.1 probability
AUG_MAX_RATE = 0.3
AUG_MIN_RATE = 0.01


def read_lines(path):
    with zstd.open(path, "rt") as f:
        return f.readlines()


def is_title_case(text):
    return all((word[0].isupper() or not word.isalpha()) for word in text.split())


def is_upper_case(text):
    return all((word.isupper() or not word.isalpha()) for word in text.split())


def get_aug_rate(file, check_func):
    lines = read_lines(file)
    aug_num = len([l for l in lines if check_func(l)])
    rate = aug_num / len(lines)
    print(f"augmentation rate for {file}: {rate}")
    return rate


@pytest.fixture(scope="function")
def data_dir():
    return DataDir("test_data_importer")


@pytest.mark.parametrize(
    "importer,dataset",
    [
        ("mtdata", "Neulab-tedtalks_test-1-eng-rus"),
        ("opus", "ELRC-3075-wikipedia_health_v1"),
        ("flores", "dev"),
        ("sacrebleu", "wmt19"),
        ("bucket", "releng-translations-dev_data_en-ru_pytest-dataset"),
    ],
)
def test_basic_corpus_import(importer, dataset, data_dir):
    data_dir.run_task(
        f"dataset-{importer}-{dataset}-en-ru",
        env={
            "COMPRESSION_CMD": COMPRESSION_CMD,
            "ARTIFACT_EXT": ARTIFACT_EXT,
            "WGET": os.path.join(CURRENT_FOLDER, "fixtures/wget"),
            "MOCKED_DOWNLOADS": get_mocked_downloads(),
        },
    )

    prefix = data_dir.join(f"artifacts/{dataset}")
    output_src = f"{prefix}.ru.{ARTIFACT_EXT}"
    output_trg = f"{prefix}.en.{ARTIFACT_EXT}"

    assert os.path.exists(output_src)
    assert os.path.exists(output_trg)
    assert len(read_lines(output_src)) > 0
    assert len(read_lines(output_trg)) > 0


@pytest.mark.parametrize(
    "importer,dataset,first_line",
    [
        ("news-crawl", "news_2021", 5),
        ("bucket", "releng-translations-dev_data_en-ru_pytest-dataset", 0),
    ],
)
def test_mono_source_import(importer, dataset, first_line, data_dir):
    data_dir.run_task(
        f"dataset-{importer}-{dataset}-en",
        env={
            "COMPRESSION_CMD": COMPRESSION_CMD,
            "ARTIFACT_EXT": ARTIFACT_EXT,
            "WGET": os.path.join(CURRENT_FOLDER, "fixtures/wget"),
            "MOCKED_DOWNLOADS": get_mocked_downloads(),
        },
    )

    prefix = data_dir.join(f"artifacts/{dataset}")
    mono_data = f"{prefix}.en.{ARTIFACT_EXT}"

    data_dir.print_tree()

    en_lines = en_sample.splitlines(keepends=True)

    assert os.path.exists(mono_data)
    source_lines = read_lines(mono_data)
    assert len(source_lines) == len(en_lines)
    assert source_lines[0] == en_lines[first_line], "The data is shuffled."


@pytest.mark.parametrize(
    "importer,dataset,first_line",
    [
        ("news-crawl", "news_2021", 5),
        ("bucket", "releng-translations-dev_data_en-ru_pytest-dataset", 0),
    ],
)
def test_mono_target_import(importer, dataset, first_line, data_dir):
    data_dir.run_task(
        f"dataset-{importer}-{dataset}-ru",
        env={
            "COMPRESSION_CMD": COMPRESSION_CMD,
            "ARTIFACT_EXT": ARTIFACT_EXT,
            "WGET": os.path.join(CURRENT_FOLDER, "fixtures/wget"),
            "MOCKED_DOWNLOADS": get_mocked_downloads(),
        },
    )

    prefix = data_dir.join(f"artifacts/{dataset}")
    mono_data = f"{prefix}.ru.{ARTIFACT_EXT}"

    ru_lines = ru_sample.splitlines(keepends=True)

    data_dir.print_tree()
    source_lines = read_lines(mono_data)
    assert len(source_lines) == len(ru_lines)
    assert source_lines[0] == ru_lines[first_line], "The data is shuffled."


augmentation_params = [
    ("sacrebleu_aug-upper_wmt19", is_upper_case, AUG_MIN_RATE, AUG_MAX_RATE),
    ("sacrebleu_aug-upper-strict_wmt19", is_upper_case, 1.0, 1.0),
    ("sacrebleu_aug-title_wmt19", is_title_case, AUG_MIN_RATE, AUG_MAX_RATE),
    ("sacrebleu_aug-title-strict_wmt19", is_title_case, 1.0, 1.0),
]


@pytest.mark.parametrize("params", augmentation_params, ids=[d[0] for d in augmentation_params])
def test_specific_augmentation(params, data_dir):
    dataset, check_func, min_rate, max_rate = params
    prefix = data_dir.join(dataset)
    output_src = f"{prefix}.{SRC}.{ARTIFACT_EXT}"
    output_trg = f"{prefix}.{TRG}.{ARTIFACT_EXT}"

    run_import("corpus", dataset, prefix)

    data_dir.print_tree()
    assert os.path.exists(output_src)
    assert os.path.exists(output_trg)

    for file in (output_src, output_trg):
        rate = get_aug_rate(file, check_func)
        assert rate >= min_rate
        assert rate <= max_rate


def test_augmentation_mix(data_dir):
    dataset = "sacrebleu_aug-mix_wmt19"
    prefix = data_dir.join(dataset)
    output_src = f"{prefix}.{SRC}.{ARTIFACT_EXT}"
    output_trg = f"{prefix}.{TRG}.{ARTIFACT_EXT}"

    run_import("corpus", dataset, prefix)

    data_dir.print_tree()
    assert os.path.exists(output_src)
    assert os.path.exists(output_trg)

    for file in (output_src, output_trg):
        for check_func in (is_upper_case, is_title_case):
            rate = get_aug_rate(file, check_func)
            assert rate <= AUG_MAX_RATE
            assert rate >= AUG_MIN_RATE

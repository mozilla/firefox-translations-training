import gzip
import os
import shutil

import pytest

SRC = "ru"
TRG = "en"
ARTIFACT_EXT = "gz"

os.environ["ARTIFACT_EXT"] = ARTIFACT_EXT
os.environ["COMPRESSION_CMD"] = "pigz"
os.environ["SRC"] = SRC
os.environ["TRG"] = TRG

from pipeline.data.dataset_importer import run_import

OUTPUT_DIR = "tests_data"
# the augmentation is probabilistic, here is a range for 0.1 probability
AUG_MAX_RATE = 0.3
AUG_MIN_RATE = 0.01


def read_lines(path):
    with gzip.open(path, "rt") as f:
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
def output_dir():
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)
    return os.path.abspath(OUTPUT_DIR)


@pytest.mark.parametrize(
    "dataset",
    [
        "mtdata_Neulab-tedtalks_test-1-eng-rus",
        "opus_ELRC-3075-wikipedia_health/v1",
        "flores_dev",
        "sacrebleu_wmt19",
    ],
)
def test_basic_corpus_import(dataset, output_dir):
    prefix = os.path.join(output_dir, dataset)
    output_src = f"{prefix}.{SRC}.{ARTIFACT_EXT}"
    output_trg = f"{prefix}.{TRG}.{ARTIFACT_EXT}"

    run_import("corpus", dataset, prefix)

    assert os.path.exists(output_src)
    assert os.path.exists(output_trg)
    assert len(read_lines(output_src)) > 0
    assert len(read_lines(output_trg)) > 0


@pytest.mark.parametrize(
    "params",
    [
        ("sacrebleu_aug-upper_wmt19", is_upper_case, AUG_MIN_RATE, AUG_MAX_RATE),
        ("sacrebleu_aug-upper-strict_wmt19", is_upper_case, 1.0, 1.0),
        ("sacrebleu_aug-title_wmt19", is_title_case, AUG_MIN_RATE, AUG_MAX_RATE),
        ("sacrebleu_aug-title-strict_wmt19", is_title_case, 1.0, 1.0),
    ],
)
def test_specific_augmentation(params, output_dir):
    dataset, check_func, min_rate, max_rate = params
    prefix = os.path.join(output_dir, dataset)
    output_src = f"{prefix}.{SRC}.{ARTIFACT_EXT}"
    output_trg = f"{prefix}.{TRG}.{ARTIFACT_EXT}"

    run_import("corpus", dataset, prefix)

    assert os.path.exists(output_src)
    assert os.path.exists(output_trg)

    for file in (output_src, output_trg):
        rate = get_aug_rate(file, check_func)
        assert rate >= min_rate
        assert rate <= max_rate


def test_augmentation_mix(output_dir):
    dataset = "sacrebleu_aug-mix_wmt19"
    prefix = os.path.join(output_dir, dataset)
    output_src = f"{prefix}.{SRC}.{ARTIFACT_EXT}"
    output_trg = f"{prefix}.{TRG}.{ARTIFACT_EXT}"

    run_import("corpus", dataset, prefix)

    assert os.path.exists(output_src)
    assert os.path.exists(output_trg)

    for file in (output_src, output_trg):
        for check_func in (is_upper_case, is_title_case):
            rate = get_aug_rate(file, check_func)
            assert rate <= AUG_MAX_RATE
            assert rate >= AUG_MIN_RATE

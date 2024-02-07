import gzip
import os

import pytest
from fixtures import DataDir, get_mocked_downloads

SRC = "ru"
TRG = "en"
ARTIFACT_EXT = "gz"
COMPRESSION_CMD = "pigz"
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
    with gzip.open(path, "rt") as f:
        return f.readlines()


def is_title_case(text):
    return all((word[0].isupper() or not word.isalpha()) for word in text.split())


def is_title_lines(src_l, trg_l, aug_src_l, aug_trg_l):
    return is_title_case(aug_src_l) and is_title_case(aug_trg_l)


def is_upper_case(text):
    return all((word.isupper() or not word.isalpha()) for word in text.split())


def is_upper_lines(src_l, trg_l, aug_src_l, aug_trg_l):
    return is_upper_case(aug_src_l) and is_upper_case(aug_trg_l)


def src_is_different(src_l, trg_l, aug_src_l, aug_trg_l):
    return src_l != aug_src_l


def all_equal(*items):
    assert len(set(items)) == 1


def twice_longer(src, trg, aug_src, aug_trg):
    assert src * 2 == aug_src
    assert trg * 2 == aug_trg


def get_aug_rate(src, trg, aug_src, aug_trg, check_func, check_len=None):
    src, trg, aug_src, aug_trg = (
        read_lines(src),
        read_lines(trg),
        read_lines(aug_src),
        read_lines(aug_trg),
    )
    if check_len:
        check_len(len(src), len(trg), len(aug_src), len(aug_trg))

    if len(src) != len(aug_src):
        rate = 0
    else:
        aug_num = 0
        for lines in zip(src, trg, aug_src, aug_trg):
            if check_func(*lines):
                aug_num += 1
        rate = aug_num / len(src)

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
    output_src = f"{prefix}.ru.gz"
    output_trg = f"{prefix}.en.gz"

    assert os.path.exists(output_src)
    assert os.path.exists(output_trg)
    assert len(read_lines(output_src)) > 0
    assert len(read_lines(output_trg)) > 0


@pytest.mark.parametrize(
    "params",
    [
        ("sacrebleu_aug-upper_wmt19", is_upper_lines, all_equal, 1.0, 1.0),
        ("sacrebleu_aug-title_wmt19", is_title_lines, all_equal, 1.0, 1.0),
        # there's a small chance for the string to stay the same
        ("sacrebleu_aug-typos_wmt19", src_is_different, all_equal, 0.95, 1.0),
        # noise modifier generates extra lines
        ("sacrebleu_aug-noise_wmt19", lambda x: True, twice_longer, 0.0, 0.0),
    ],
    ids=["upper", "title", "typos", "noise"],
)
def test_specific_augmentation(params, data_dir):
    dataset, check_func, check_len, min_rate, max_rate = params
    original_dataset = "sacrebleu_wmt19"
    prefix_aug = data_dir.join(dataset)
    prefix_original = data_dir.join(original_dataset)
    output_src = f"{prefix_aug}.{SRC}.{ARTIFACT_EXT}"
    output_trg = f"{prefix_aug}.{TRG}.{ARTIFACT_EXT}"
    original_src = f"{prefix_original}.{SRC}.{ARTIFACT_EXT}"
    original_trg = f"{prefix_original}.{TRG}.{ARTIFACT_EXT}"
    run_import("corpus", original_dataset, prefix_original)

    run_import("corpus", dataset, prefix_aug)

    assert os.path.exists(output_src)
    assert os.path.exists(output_trg)
    rate = get_aug_rate(original_src, original_trg, output_src, output_trg, check_func, check_len)
    assert rate >= min_rate
    assert rate <= max_rate


def test_augmentation_mix(data_dir):
    dataset = "sacrebleu_aug-mix_wmt19"
    original_dataset = "sacrebleu_wmt19"
    prefix = data_dir.join(dataset)
    prefix_original = data_dir.join(original_dataset)
    output_src = f"{prefix}.{SRC}.{ARTIFACT_EXT}"
    output_trg = f"{prefix}.{TRG}.{ARTIFACT_EXT}"
    original_src = f"{prefix_original}.{SRC}.{ARTIFACT_EXT}"
    original_trg = f"{prefix_original}.{TRG}.{ARTIFACT_EXT}"
    run_import("corpus", original_dataset, prefix_original)

    run_import("corpus", dataset, prefix)

    assert os.path.exists(output_src)
    assert os.path.exists(output_trg)
    src, trg, aug_src, aug_trg = (
        read_lines(original_src),
        read_lines(original_trg),
        read_lines(output_src),
        read_lines(output_trg),
    )
    len_noise_src = len(aug_src) - len(src)
    len_noise_trg = len(aug_trg) - len(trg)
    # check noise rate
    for noise, original in [(len_noise_src, len(src)), (len_noise_trg, len(trg))]:
        noise_rate = noise / original
        assert noise_rate > AUG_MIN_RATE
        assert noise_rate < AUG_MAX_RATE

    # check augmentation rate without noise
    for aug, original in [(aug_src, src), (aug_trg, trg)]:
        len_unchanged = len(set(aug).intersection(set(original)))
        len_original = len(original)
        aug_rate = (len_original - len_unchanged) / len(original)
        assert aug_rate > AUG_MIN_RATE
        assert aug_rate < AUG_MAX_RATE

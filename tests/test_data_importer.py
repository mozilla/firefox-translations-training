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

from pipeline.data import dataset_importer
from pipeline.data.dataset_importer import run_import


def add_fake_alignments(corpus):
    corpus_and_aln = []
    for line in corpus:
        parts = line.split("\t")
        src_sent, trg_sent = parts[0], parts[1]
        min_len = min(len(src_sent.split()), len(trg_sent.split()))
        aln = " ".join([f"{idx}-{idx}" for idx in range(min_len)])
        corpus_and_aln.append(f"{line}\t{aln}")

    return corpus_and_aln


# it's very slow to download and run BERT on 2000 lines
dataset_importer.add_alignments = add_fake_alignments


def read_lines(path):
    with zstd.open(path, "rt") as f:
        return f.readlines()


def is_title_case(text):
    return all((word[0].isupper() or not word.isalpha()) for word in text.split())


def is_title_lines(src_l, trg_l, aug_src_l, aug_trg_l):
    return is_title_case(aug_src_l) and is_title_case(aug_trg_l)


def is_upper_case(text):
    return all((word.isupper() or not word.isalpha()) for word in text.split())


def is_upper_lines(src_l, trg_l, aug_src_l, aug_trg_l):
    return is_upper_case(aug_src_l) and is_upper_case(aug_trg_l)


def only_src_is_different(src_l, trg_l, aug_src_l, aug_trg_l):
    return src_l != aug_src_l and trg_l == aug_trg_l


def src_and_trg_are_different(src_l, trg_l, aug_src_l, aug_trg_l):
    return src_l != aug_src_l and trg_l != aug_trg_l


def aug_lines_are_not_too_long(src_l, trg_l, aug_src_l, aug_trg_l):
    return (
        len(src_l) <= len(aug_src_l)
        and len(trg_l) <= len(aug_trg_l)
        # when Tags modifier is enabled with 1.0 probability it generates too many noise insertions in each sentence
        # the length ratio can still be high for one word sentences
        and len(aug_src_l) < len(src_l) * 4
        and len(aug_trg_l) < len(trg_l) * 4
    )


def all_len_equal(*items):
    return len(set(items)) == 1


def twice_longer(src, trg, aug_src, aug_trg):
    return src * 2 == aug_src and trg * 2 == aug_trg


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
        ("url", "gcp_pytest-dataset_a0017e"),
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


mono_params = [
    ("news-crawl", "en", "news_2021",                    [0, 1, 4, 6, 3, 7, 5, 2]),
    ("news-crawl", "ru", "news_2021",                    [0, 1, 4, 6, 3, 7, 5, 2]),
    ("url",        "en", "gcp_pytest-dataset_en_cdd0d7", [2, 1, 5, 4, 0, 7, 6, 3]),
    ("url",        "ru", "gcp_pytest-dataset_ru_be3263", [5, 4, 2, 0, 7, 1, 3, 6]),
]  # fmt: skip


@pytest.mark.parametrize(
    "importer,language,dataset,sort_order",
    mono_params,
    ids=[f"{d[0]}-{d[1]}" for d in mono_params],
)
def test_mono_source_import(importer, language, dataset, sort_order, data_dir):
    data_dir.run_task(
        f"dataset-{importer}-{dataset}-{language}",
        env={
            "COMPRESSION_CMD": COMPRESSION_CMD,
            "ARTIFACT_EXT": ARTIFACT_EXT,
            "WGET": os.path.join(CURRENT_FOLDER, "fixtures/wget"),
            "MOCKED_DOWNLOADS": get_mocked_downloads(),
        },
    )

    prefix = data_dir.join(f"artifacts/{dataset}")
    mono_data = f"{prefix}.{language}.{ARTIFACT_EXT}"

    data_dir.print_tree()

    sample = {
        "en": en_sample,
        "ru": ru_sample,
    }

    sample_lines = sample[language].splitlines(keepends=True)

    assert os.path.exists(mono_data)
    source_lines = list(read_lines(mono_data))
    assert [
        source_lines.index(line) for line in sample_lines
    ] == sort_order, "The data is shuffled."


@pytest.mark.parametrize(
    "params",
    [
        ("sacrebleu_aug-upper_wmt19", is_upper_lines, all_len_equal, None, 1.0, 1.0),
        ("sacrebleu_aug-title_wmt19", is_title_lines, all_len_equal, None, 1.0, 1.0),
        # there's a small chance for the string to stay the same
        ("sacrebleu_aug-typos_wmt19", only_src_is_different, all_len_equal, None, 0.95, 1.0),
        # noise modifier generates extra lines
        ("sacrebleu_aug-noise_wmt19", lambda x: True, twice_longer, None, 0.0, 0.0),
        (
            "sacrebleu_aug-inline-noise_wmt19",
            src_and_trg_are_different,
            all_len_equal,
            aug_lines_are_not_too_long,
            # we reduce probability otherwise it generates too much noise in each sentence
            0.4,
            0.7,
        ),
    ],
    ids=["upper", "title", "typos", "noise", "inline-noise"],
)
def test_specific_augmentation(params, data_dir):
    dataset, check_is_aug, check_corpus_len, check_lines, min_rate, max_rate = params
    original_dataset = "sacrebleu_wmt19"
    prefix_aug = data_dir.join(dataset)
    prefix_original = data_dir.join(original_dataset)
    output_src = f"{prefix_aug}.{SRC}.{ARTIFACT_EXT}"
    output_trg = f"{prefix_aug}.{TRG}.{ARTIFACT_EXT}"
    original_src = f"{prefix_original}.{SRC}.{ARTIFACT_EXT}"
    original_trg = f"{prefix_original}.{TRG}.{ARTIFACT_EXT}"
    run_import("corpus", original_dataset, prefix_original)

    run_import("corpus", dataset, prefix_aug)

    data_dir.print_tree()
    assert os.path.exists(output_src)
    assert os.path.exists(output_trg)
    src, trg, aug_src, aug_trg = (
        read_lines(original_src),
        read_lines(original_trg),
        read_lines(output_src),
        read_lines(output_trg),
    )
    assert check_corpus_len(len(src), len(trg), len(aug_src), len(aug_trg))
    if len(src) == len(aug_src):
        aug_num = 0
        for lines in zip(src, trg, aug_src, aug_trg):
            if check_lines:
                assert check_lines(*lines)
            if check_is_aug(*lines):
                aug_num += 1
        rate = aug_num / len(src)
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

    AUG_MAX_RATE = 0.35
    AUG_MIN_RATE = 0.01
    data_dir.print_tree()
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

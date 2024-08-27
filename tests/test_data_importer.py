import json
import os

import pytest
import zstandard as zstd
from fixtures import DataDir, en_sample, get_mocked_downloads, ru_sample

SRC = "ru"
TRG = "en"
CURRENT_FOLDER = os.path.dirname(os.path.abspath(__file__))

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
            "WGET": os.path.join(CURRENT_FOLDER, "fixtures/wget"),
            "MOCKED_DOWNLOADS": get_mocked_downloads(),
        },
    )

    prefix = data_dir.join(f"artifacts/{dataset}")
    output_src = f"{prefix}.ru.zst"
    output_trg = f"{prefix}.en.zst"

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
            "WGET": os.path.join(CURRENT_FOLDER, "fixtures/wget"),
            "MOCKED_DOWNLOADS": get_mocked_downloads(),
        },
    )

    prefix = data_dir.join(f"artifacts/{dataset}")
    mono_data = f"{prefix}.{language}.zst"

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


hplt_translations = {
    "en": [
        "5. Download the driver which you want. There may be numerous variations shown. Pick the latest one.\n",
        "2.In the search box, enter Update, and then, in the list of results, select Windows Update.\n",
        "All transactions are covered by our general terms and conditions of sale. Below are additional terms, applicable for online sales only.\n",
        "Commercial dishwashers\n",
        "Competitive Advantage\n",
        "This post is just the ticket for those of you who love your tablet or anyone who wants to TURN_ON PC. Getting an error code in your UAVG and don't know what it means? We have come up with the best four method to settle it. Finish this article and you will be suddenly enlightened.\n",
        '5. Confirm that you want to uninstall a program by clicking on the "Yes" button.\n',
        "The user currently does not have any images...\n",
        '3. Depending on your view options either click on "uninstall a program" or "program and features".\n',
        "Get a great deal on our range of used industrial washers.\n",
    ],
    "ru": [
        "Научные школы и направления\n",
        "Организации, признанные экстремистскими и запрещённые на территории РФ\n",
        "Получение направления\n",
        "– Современные проблемы истории и теории государства и права.\n",
        "Большинство вело маршрутов в Новой Зеландии оцениваются по степени сложности:\n",
        "Член конгресса США от Республиканской партии Дана Рорабахер не поддержал предложение сопредседателя партии РПР-ПАРНАС Михаила Касьянова ввести санкции в отношении некоторых представителей российских средств массовой информации.\n",
        "мы хотим сделать для них дополнительные активности, планировали мы лазертаг, экскурсии какие-то... Не до конца понятно, как это можно будет совмещать.\n",
        "Самоуправления\n",
        "Поэтому никакой критической ситуации сейчас нет, как и необходимости вводить какие-либо ограничения на федеральном уровне. Но рекомендуется следовать стандартным мерам предосторожности — носить маски в общественных местах, соблюдать гигиену рук. Это крайне важно для уязвимых категорий граждан. Также следует вакцинироваться, если подошло время.\n",
        "Предложения расширить список Магнитского звучат не впервые. В начале марта помощник госсекретаря США по вопросам Европы и Евразии Виктория Нуланд призвала это сделать также из-за убийства Бориса Немцова.\n",
    ],
}

hplt_stats = {
    "en": {
        "shards": {"filtered": 1, "kept": 1},
        "oversampling": {"filtered": 1514, "kept": 200},
        "final": {"filtered": 1614, "kept": 100},
        "document_count": 15,
    },
    "ru": {
        "shards": {"filtered": 1, "kept": 1},
        "oversampling": {"filtered": 2337, "kept": 200},
        "final": {"filtered": 2437, "kept": 100},
        "document_count": 23,
    },
}


@pytest.mark.parametrize(
    "language",
    ["ru", "en"],
)
def test_mono_hplt(language, data_dir: DataDir):
    dataset = "mono_v1_2"
    data_dir.print_tree()
    max_sentences = 100

    data_dir.run_task(
        f"dataset-hplt-{dataset}-{language}",
        env={
            "MOCKED_DOWNLOADS": get_mocked_downloads(),
        },
        extra_args=["--max_sentences", str(max_sentences)],
    )
    data_dir.print_tree()

    lines = read_lines(data_dir.join(f"artifacts/{dataset}.{language}.zst"))
    assert lines[:10] == hplt_translations[language]

    assert len(lines) == max_sentences

    assert (
        json.loads(data_dir.load(f"artifacts/{dataset}.{language}.stats.json"))
        == hplt_stats[language]
    )


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
    output_src = f"{prefix_aug}.{SRC}.zst"
    output_trg = f"{prefix_aug}.{TRG}.zst"
    original_src = f"{prefix_original}.{SRC}.zst"
    original_trg = f"{prefix_original}.{TRG}.zst"
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
    output_src = f"{prefix}.{SRC}.zst"
    output_trg = f"{prefix}.{TRG}.zst"
    original_src = f"{prefix_original}.{SRC}.zst"
    original_trg = f"{prefix_original}.{TRG}.zst"
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

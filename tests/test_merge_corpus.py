import pytest
from fixtures import DataDir

from pipeline.common.downloads import read_lines

ada_en = """ADA 1
ADA 2
ADA 3
SHARED 1
SHARED 2
ADA 4
ADA 5
"""

wiki_en = """WIKI 1
WIKI 2
SHARED 3
SHARED 4
WIKI 3
SHARED 1
WIKI 4
"""

web_acquired_en = """WEB_ACQUIRED 1
WEB_ACQUIRED 2
SHARED 3
SHARED 4
WEB_ACQUIRED 3
SHARED 2
WEB_ACQUIRED 4
"""

ada_ru = """АДА 1
АДА 2
АДА 3
ШАРЕД 1
ШАРЕД 2
АДА 4
АДА 5
"""

wiki_ru = """WИКИ 1
WИКИ 2
ШАРЕД 3
ШАРЕД 4
WИКИ 3
ШАРЕД 1
WИКИ 4
"""

web_acquired_ru = """WЕБ_АЦQУИРЕД 1
WЕБ_АЦQУИРЕД 2
ШАРЕД 3
ШАРЕД 4
WЕБ_АЦQУИРЕД 3
ШАРЕД 2
WЕБ_АЦQУИРЕД 4
"""


@pytest.fixture(scope="function")
def data_dir():
    data_dir = DataDir("test_merge_corpus")
    data_dir.mkdir("artifacts")
    data_dir.create_zst("ada83_v1.en.zst", ada_en)
    data_dir.create_zst("ada83_v1.ru.zst", ada_ru)
    data_dir.create_zst("ELRC-3075-wikipedia_health_v1.en.zst", wiki_en)
    data_dir.create_zst("ELRC-3075-wikipedia_health_v1.ru.zst", wiki_ru)
    data_dir.create_zst("ELRC-web_acquired_data.en.zst", web_acquired_en)
    data_dir.create_zst("ELRC-web_acquired_data.ru.zst", web_acquired_ru)
    return data_dir


def assert_datasets(data_dir: DataDir, en_path: str, ru_path: str):
    with read_lines(data_dir.join(en_path)) as lines_iter:
        corpus_lines = list(lines_iter)
        assert corpus_lines == [
            "WIKI 1\n",
            "ADA 5\n",
            "WEB_ACQUIRED 2\n",
            "SHARED 3\n",
            "ADA 3\n",
            "WEB_ACQUIRED 1\n",
            "SHARED 4\n",
            "WEB_ACQUIRED 4\n",
            "ADA 2\n",
            "WIKI 4\n",
            "WIKI 3\n",
            "SHARED 2\n",
            "WIKI 2\n",
            "SHARED 1\n",
            "ADA 4\n",
            "ADA 1\n",
            "WEB_ACQUIRED 3\n",
        ]

    with read_lines(data_dir.join(ru_path)) as lines_iter:
        corpus_lines = list(lines_iter)
        assert corpus_lines == [
            "WИКИ 1\n",
            "АДА 5\n",
            "WЕБ_АЦQУИРЕД 2\n",
            "ШАРЕД 3\n",
            "АДА 3\n",
            "WЕБ_АЦQУИРЕД 1\n",
            "ШАРЕД 4\n",
            "WЕБ_АЦQУИРЕД 4\n",
            "АДА 2\n",
            "WИКИ 4\n",
            "WИКИ 3\n",
            "ШАРЕД 2\n",
            "WИКИ 2\n",
            "ШАРЕД 1\n",
            "АДА 4\n",
            "АДА 1\n",
            "WЕБ_АЦQУИРЕД 3\n",
        ]


def test_merge_corpus(data_dir):
    data_dir.run_task(
        "merge-corpus-en-ru",
    )
    data_dir.print_tree()
    assert_datasets(data_dir, "artifacts/corpus.en.zst", "artifacts/corpus.ru.zst")


def test_merge_devset(data_dir):
    data_dir.run_task(
        "merge-devset-en-ru",
    )
    data_dir.print_tree()
    assert_datasets(data_dir, "artifacts/devset.en.zst", "artifacts/devset.ru.zst")


def assert_trimmed_datasets(data_dir: DataDir, en_path: str, ru_path: str):
    with read_lines(data_dir.join(en_path)) as lines_iter:
        corpus_lines = list(lines_iter)
        assert corpus_lines == [
            "ADA 1\n",
            "WEB_ACQUIRED 4\n",
            "WEB_ACQUIRED 3\n",
            "ADA 4\n",
            "WEB_ACQUIRED 2\n",
            "SHARED 2\n",
            "SHARED 1\n",
            "WIKI 2\n",
            "ADA 5\n",
            "ADA 3\n",
        ]

    with read_lines(data_dir.join(ru_path)) as lines_iter:
        corpus_lines = list(lines_iter)
        assert corpus_lines == [
            "АДА 1\n",
            "WЕБ_АЦQУИРЕД 4\n",
            "WЕБ_АЦQУИРЕД 3\n",
            "АДА 4\n",
            "WЕБ_АЦQУИРЕД 2\n",
            "ШАРЕД 2\n",
            "ШАРЕД 1\n",
            "WИКИ 2\n",
            "АДА 5\n",
            "АДА 3\n",
        ]


def test_merge_devset_trimmed(data_dir):
    data_dir.run_task(
        "merge-devset-en-ru",
        # Replace the max_sentences.
        replace_args=[("None", "10")],
    )
    data_dir.print_tree()
    assert_trimmed_datasets(data_dir, "artifacts/devset.en.zst", "artifacts/devset.ru.zst")


def test_merge_corpus_trimmed(data_dir):
    data_dir.run_task(
        "merge-corpus-en-ru",
        # Replace the max_sentences.
        replace_args=[("None", "10")],
    )
    data_dir.print_tree()
    assert_trimmed_datasets(data_dir, "artifacts/corpus.en.zst", "artifacts/corpus.ru.zst")

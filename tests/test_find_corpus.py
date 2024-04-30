from textwrap import dedent

import pytest

from utils.find_corpus import main as find_corpus

"""
Tests the `utils/find_corpus.py` script.
"""


@pytest.fixture
def mock_opus_data(requests_mock):
    """
    Provide a simplistic response from opus, with only 2 entries.
    """
    requests_mock.get(
        "https://opus.nlpl.eu/opusapi/?source=en&target=ca&preprocessing=moses&version=latest",
        text="""{
            "corpora": [
                {
                    "alignment_pairs": 4605,
                    "corpus": "Books",
                    "documents": "",
                    "id": 31736,
                    "latest": "True",
                    "preprocessing": "moses",
                    "size": 328,
                    "source": "ca",
                    "source_tokens": 73463,
                    "target": "en",
                    "target_tokens": 68625,
                    "url": "https://object.pouta.csc.fi/OPUS-Books/v1/moses/ca-en.txt.zip",
                    "version": "v1"
                },
                {
                    "alignment_pairs": 5802549,
                    "corpus": "CCAligned",
                    "documents": "",
                    "id": 32571,
                    "latest": "True",
                    "preprocessing": "moses",
                    "size": 522860,
                    "source": "ca",
                    "source_tokens": 89704109,
                    "target": "en",
                    "target_tokens": 84373417,
                    "url": "https://object.pouta.csc.fi/OPUS-CCAligned/v1/moses/ca-en.txt.zip",
                    "version": "v1"
                }
            ]
        }""",
    )


def assert_stdout(capsys, message: str, expected_output: str):
    """
    Asserts the output from stdout matches a certain string.
    """
    captured = capsys.readouterr()

    def clean_text(text):
        text = dedent(text).strip()
        result = ""
        for line in text.split("\n"):
            result += line.strip() + "\n"
        return result

    assert clean_text(captured.out) == clean_text(expected_output), message


def test_opus(mock_opus_data, capsys):
    find_corpus(["en", "ca", "--importer", "opus"])
    assert_stdout(
        capsys,
        "The opus dataset outputs nicely.",
        """
        Fetching datasets from:
        https://opus.nlpl.eu/opusapi/?source=en&target=ca&preprocessing=moses&version=latest


        ┌──────────────────────────────┐
        │ OPUS - https://opus.nlpl.eu/ │
        └──────────────────────────────┘

        Dataset   Code              Sentences Size     URL
        ───────── ───────────────── ───────── ──────── ─────────────────────────────────────────────────
        CCAligned opus_CCAligned/v1 5802549   535.4 MB https://opus.nlpl.eu/CCAligned/ca&en/v1/CCAligned
        Books     opus_Books/v1     4605      335.9 kB https://opus.nlpl.eu/Books/ca&en/v1/Books

        YAML:
            - opus_Books/v1
            - opus_CCAligned/v1
        """,
    )


def test_opus_download_url(mock_opus_data, capsys):
    """
    This checks that the download URLs are shown instead of the information URLs.
    """
    find_corpus(["en", "ca", "--importer", "opus", "--download_url"])
    output = capsys.readouterr()
    assert "https://object.pouta.csc.fi/OPUS-CCAligned/v1/moses/ca-en.txt.zip" in output.out
    assert "https://object.pouta.csc.fi/OPUS-Books/v1/moses/ca-en.txt.zip" in output.out


# mtdata has some deprecated dependencies
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_mtdata(requests_mock, capsys):
    find_corpus(["en", "ca", "--importer", "mtdata"])
    assert_stdout(
        capsys,
        "mtdata outputs nicely",
        """
        ┌────────────────────────────────────────────────┐
        │ mtdata - https://github.com/thammegowda/mtdata │
        └────────────────────────────────────────────────┘

        Dataset                                URL
        ────────────────────────────────────── ───────────────────────────────────────────────────────────────────────────────────────────────────────────
        mtdata_ELRC-wikipedia_health-1-cat-eng https://elrc-share.eu/repository/download/ac6d557e8de811ea913100155d026706b0c5fee96b88489781ddd7675f8ea2ae/
        mtdata_Facebook-wikimatrix-1-cat-eng   https://dl.fbaipublicfiles.com/laser/WikiMatrix/v1/WikiMatrix.ca-en.tsv.gz
        mtdata_Statmt-ccaligned-1-cat_ES-eng   http://www.statmt.org/cc-aligned/sentence-aligned/ca_ES-en_XX.tsv.xz

        YAML:
            - mtdata_ELRC-wikipedia_health-1-cat-eng
            - mtdata_Facebook-wikimatrix-1-cat-eng
            - mtdata_Statmt-ccaligned-1-cat_ES-eng
        """,
    )


def test_sacrebleu(requests_mock, capsys):
    # "iu" is the Inuktitut language, which has a small dataset available.
    find_corpus(["en", "iu", "--importer", "sacrebleu"])
    assert_stdout(
        capsys,
        "sacrebleu outputs nicely",
        """
        ┌─────────────────────────────────────────────────┐
        │ sacrebleu - https://github.com/mjpost/sacrebleu │
        └─────────────────────────────────────────────────┘

        Dataset   Description                             URLs
        ───────── ─────────────────────────────────────── ──────────────────────────────────────────────────────
        wmt20     Official evaluation data for WMT20      http://data.statmt.org/wmt20/translation-task/test.tgz
        wmt20/dev Development data for tasks new to 2020. http://data.statmt.org/wmt20/translation-task/dev.tgz

        YAML:
            - sacrebleu_wmt20
            - sacrebleu_wmt20/dev
        """,
    )

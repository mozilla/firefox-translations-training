import os
import shutil

import pytest
import sentencepiece as spm
from fixtures import DataDir, en_sample, ru_sample

pytestmark = [pytest.mark.docker_amd64]

current_folder = os.path.dirname(os.path.abspath(__file__))
fixtures_path = os.path.join(current_folder, "fixtures")
root_path = os.path.abspath(os.path.join(current_folder, ".."))
bin_dir = os.environ["BIN"] if os.getenv("BIN") else os.path.join(root_path, "bin")
marian_dir = (
    os.environ["MARIAN"]
    if os.getenv("MARIAN")
    else os.path.join(root_path, "3rd_party", "marian-dev", "build")
)


def validate_alignments(corpus_path, model_path):
    sp = spm.SentencePieceProcessor(model_file=model_path)

    with open(corpus_path) as f:
        for line in f:
            fields = line.strip().split("\t")
            assert len(fields) == 3
            src = sp.encode_as_pieces(fields[0])
            trg = sp.encode_as_pieces(fields[1])
            alignment = [[int(num) for num in pair.split("-")] for pair in fields[2].split()]

            for idx_src, idx_trg in alignment:
                try:
                    assert src[idx_src] is not None
                    assert trg[idx_trg] is not None
                except:
                    print("src: ", src)
                    print("trg: ", trg)
                    print("alignment:", alignment)
                    raise


@pytest.fixture()
def data_dir():
    return DataDir("test_training")


@pytest.fixture()
def vocab(data_dir):
    shutil.copyfile("tests/data/vocab.spm", data_dir.join("vocab.spm"))


@pytest.fixture()
def corpus(data_dir):
    data_dir.create_zst("corpus.en.zst", en_sample)
    data_dir.create_zst("corpus.ru.zst", ru_sample)
    data_dir.create_zst("devset.en.zst", en_sample)
    data_dir.create_zst("devset.ru.zst", ru_sample)


@pytest.fixture()
def alignments(data_dir, vocab, corpus):
    env = {
        "TEST_ARTIFACTS": data_dir.path,
        "BIN": bin_dir,
        "MARIAN": marian_dir,
        "SRC": "en",
        "TRG": "ru",
    }
    data_dir.run_task("alignments-original-en-ru", env=env)
    shutil.copyfile(
        os.path.join(data_dir.path, "artifacts", "corpus.aln.zst"), data_dir.join("corpus.aln.zst")
    )
    # recreate corpus
    data_dir.create_zst("corpus.en.zst", en_sample)
    data_dir.create_zst("corpus.ru.zst", ru_sample)


def test_train_student_mocked(alignments, data_dir):
    """
    Run training with mocked marian to check OpusTrainer output
    """

    env = {
        "TEST_ARTIFACTS": data_dir.path,
        "BIN": bin_dir,
        "MARIAN": fixtures_path,
        "SRC": "en",
        "TRG": "ru",
    }

    data_dir.run_task("train-student-en-ru", env=env)

    assert os.path.isfile(
        os.path.join(data_dir.path, "artifacts", "final.model.npz.best-chrf.npz")
    )
    assert os.path.isfile(
        os.path.join(data_dir.path, "artifacts", "model.npz.best-chrf.npz.decoder.yml")
    )
    validate_alignments(data_dir.join("marian.input.txt"), data_dir.join("vocab.spm"))


def test_train_student(alignments, data_dir):
    """
    Run real training with Marian as an integration test
    """

    env = {
        "TEST_ARTIFACTS": data_dir.path,
        "BIN": bin_dir,
        "MARIAN": marian_dir,
        "SRC": "en",
        "TRG": "ru",
        "USE_CPU": "true",
    }
    marian_args = [
        "--disp-freq", "1",
        "--save-freq", "2",
        "--valid-freq", "2",
        "--after-batches", "2",
        "--dim-vocabs", "1000", "1000",
        "--mini-batch", "10",
        "--maxi-batch", "10",
        "--mini-batch-fit", "false",
        "--log-level", "trace",
    ]  # fmt:skip

    data_dir.run_task("train-student-en-ru", env=env, extra_args=marian_args)

    assert os.path.isfile(
        os.path.join(data_dir.path, "artifacts", "final.model.npz.best-chrf.npz")
    )
    assert os.path.isfile(
        os.path.join(data_dir.path, "artifacts", "model.npz.best-chrf.npz.decoder.yml")
    )

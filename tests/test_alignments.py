import os

import sh
from fixtures import DataDir, en_sample, ru_sample

current_folder = os.path.dirname(os.path.abspath(__file__))
fixtures_path = os.path.join(current_folder, "fixtures")
root_path = os.path.abspath(os.path.join(current_folder, ".."))


def verify_aln(data_dir, dataset, src_corpus, trg_corpus):
    aln_path = os.path.join(data_dir.path, "artifacts", f"{dataset}.aln.zst")
    assert os.path.exists(aln_path)

    sh.zstd("-d", aln_path)
    with open(aln_path[:-4], "r") as f:
        aln_lines = f.readlines()

    src_lines = src_corpus.strip().split("\n")
    trg_lines = trg_corpus.strip().split("\n")
    assert len(aln_lines) == len(src_lines)
    assert len(aln_lines) == len(trg_lines)

    # verify alignment indices
    for aln_line, src_line, trg_line in zip(aln_lines, src_lines, trg_lines):
        alns = [pair.split("-") for pair in aln_line.split()]
        src_tokens_num = len(src_line.split())
        trg_tokens_num = len(trg_line.split())

        assert all(
            int(src_idx) < src_tokens_num and int(trg_idx) < trg_tokens_num
            for src_idx, trg_idx in alns
        )


def test_space_tokenized_aln():
    bin_dir = os.getenv("BIN")
    data_dir = DataDir("test_alignments")
    data_dir.create_zst("corpus.en.zst", en_sample),
    data_dir.create_zst("corpus.ru.zst", ru_sample),
    env = {
        "TEST_ARTIFACTS": data_dir.path,
        "BIN": bin_dir if bin_dir else os.path.join(root_path, "bin"),
        "COMPRESSION_CMD": "zstd",
        "ARTIFACT_EXT": "zst",
        "SRC": "en",
        "TRG": "ru",
    }

    data_dir.run_task("alignments-student-en-ru", env=env)

    verify_aln(data_dir, "corpus", en_sample, ru_sample)


def test_space_tokenized_aln_merged():
    data_dir = DataDir("test_alignments")
    data_dir.create_zst("corpus.en.zst", en_sample),
    data_dir.create_zst("corpus.ru.zst", ru_sample),
    mono_en_sample = "\n".join(en_sample.split("\n")[1:-1])
    mono_ru_sample = "\n".join(ru_sample.split("\n")[1:-1])
    data_dir.create_zst("mono.en.zst", mono_en_sample),
    data_dir.create_zst("mono.ru.zst", mono_ru_sample),
    env = {
        "TEST_ARTIFACTS": data_dir.path,
        "BIN": os.path.join(root_path, "bin"),
        "COMPRESSION_CMD": "zstd",
        "ARTIFACT_EXT": "zst",
        "SRC": "en",
        "TRG": "ru",
    }

    data_dir.run_task("alignments-teacher-en-ru", env=env)

    for dataset, src_corpus, trg_corpus in (
        ("corpus", en_sample, ru_sample),
        ("mono", mono_en_sample, mono_ru_sample),
    ):
        verify_aln(data_dir, dataset, src_corpus, trg_corpus)

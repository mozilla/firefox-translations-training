import os
import shutil

from fixtures import DataDir, en_sample, ru_sample

current_folder = os.path.dirname(os.path.abspath(__file__))
fixtures_path = os.path.join(current_folder, "fixtures")
root_path = os.path.abspath(os.path.join(current_folder, ".."))
bin_dir = os.environ["BIN"] if os.getenv("BIN") else os.path.join(root_path, "bin")
marian_dir = (
    os.environ["MARIAN"]
    if os.getenv("MARIAN")
    else os.path.join(root_path, "3rd_party", "marian-dev", "build")
)


def test_alignments_and_shortlist():
    data_dir = DataDir("test_shortlist")
    data_dir.create_zst("corpus.en.zst", en_sample),
    data_dir.create_zst("corpus.ru.zst", ru_sample),
    env = {
        "TEST_ARTIFACTS": data_dir.path,
        "BIN": bin_dir,
        "MARIAN": marian_dir,
        "COMPRESSION_CMD": "zstd",
        "ARTIFACT_EXT": "zst",
        "SRC": "en",
        "TRG": "ru",
    }
    shutil.copyfile("tests/data/vocab.spm", os.path.join(data_dir.path, "vocab.spm"))

    data_dir.run_task("alignments-en-ru", env=env)

    shortlist_path = os.path.join(data_dir.path, "artifacts", "lex.s2t.pruned.zst")
    assert os.path.exists(shortlist_path)
    aln_path = os.path.join(data_dir.path, "artifacts", "corpus.aln.zst")
    assert os.path.exists(aln_path)

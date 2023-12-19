import glob
import os
import random
import shutil
import string
import subprocess

import pytest
import sh

from pipeline.translate.splitter import main as split_file

COMPRESSION_CMD = "zstdmt"

OUTPUT_DIR = "data/tests_data"


@pytest.fixture(scope="function")
def clean():
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def generate_dataset(length, path):
    words = [
        "".join([random.choice(string.ascii_letters) for _ in range(random.randint(1, 10))])
        for _ in range(20)
    ]
    sentences = []
    for i in range(length):
        sentence = " ".join([words[random.randint(0, 19)] for _ in range(random.randint(1, 200))])
        sentences.append(sentence)

    with open(path, "w") as f:
        f.write("\n".join(sentences))

    sh.zstdmt(path)


def decompress(path):
    sh.zstdmt("-d", path)


def imitate_translate(dir, suffix):
    for file in glob.glob(f"{dir}/file.?.zst") + glob.glob(f"{dir}/file.??.zst"):
        print(file)
        decompress(file)
        shutil.copy(file[:-4], file[:-4] + suffix)


def read_file(path):
    with open(path) as f:
        return f.read()


def test_split_collect_mono(clean):
    os.environ["COMPRESSION_CMD"] = COMPRESSION_CMD
    length = 1234
    path = os.path.join(OUTPUT_DIR, "mono.in")
    output = os.path.join(OUTPUT_DIR, "mono.output")
    output_compressed = f"{output}.zst"
    generate_dataset(length, path)

    split_file(
        [
            f"--output_dir={OUTPUT_DIR}",
            "--num_parts=10",
            f"--compression_cmd={COMPRESSION_CMD}",
            f"{path}.zst",
        ]
    )

    expected_files = set([f"{OUTPUT_DIR}/file.{i}.zst" for i in range(1, 11)])
    assert set(glob.glob(f"{OUTPUT_DIR}/file.*.zst")) == expected_files

    imitate_translate(OUTPUT_DIR, suffix=".out")
    subprocess.run(
        ["pipeline/translate/collect.sh", OUTPUT_DIR, output_compressed, f"{path}.zst"], check=True
    )

    decompress(output_compressed)
    assert read_file(path) == read_file(output)


def test_split_collect_corpus(clean):
    os.environ["COMPRESSION_CMD"] = COMPRESSION_CMD
    length = 1234
    path_src = os.path.join(OUTPUT_DIR, "corpus.src.in")
    path_trg = os.path.join(OUTPUT_DIR, "corpus.trg.in")
    output = os.path.join(OUTPUT_DIR, "corpus.src.output")
    output_compressed = f"{output}.zst"
    generate_dataset(length, path_src)
    generate_dataset(length, path_trg)

    split_file(
        [
            f"--output_dir={OUTPUT_DIR}",
            "--num_parts=10",
            f"--compression_cmd={COMPRESSION_CMD}",
            f"{path_src}.zst",
        ]
    )
    split_file(
        [
            f"--output_dir={OUTPUT_DIR}",
            "--num_parts=10",
            f"--compression_cmd={COMPRESSION_CMD}",
            "--output_suffix=.ref",
            f"{path_trg}.zst",
        ]
    )

    expected_files = set([f"{OUTPUT_DIR}/file.{i}.zst" for i in range(1, 11)]) | set(
        [f"{OUTPUT_DIR}/file.{i}.ref.zst" for i in range(1, 11)]
    )
    assert set(glob.glob(f"{OUTPUT_DIR}/file.*.zst")) == expected_files

    imitate_translate(OUTPUT_DIR, suffix=".nbest.out")
    subprocess.run(
        ["pipeline/translate/collect.sh", OUTPUT_DIR, output_compressed, f"{path_src}.zst"],
        check=True,
    )

    decompress(output_compressed)
    assert read_file(path_src) == read_file(output)

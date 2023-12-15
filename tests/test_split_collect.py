import glob
import os
import random
import shutil
import string
import subprocess

import pytest
import sh

from pipeline.translate.splitter import split_file

OUTPUT_DIR = "tests_data"


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


def imitate_translate(dir, suffix):
    for file in glob.glob(f"{dir}/file.??"):
        shutil.copy(file, file + suffix)


def read_file(path):
    with open(path) as f:
        return f.read()


def test_split_collect_mono(clean):
    os.environ["COMPRESSION_CMD"] = "zstd"
    length = 1234
    path = os.path.join(OUTPUT_DIR, "mono.in")
    output = os.path.join(OUTPUT_DIR, "mono.output")
    output_compressed = f"{output}.zst"
    generate_dataset(length, path)
    sh.zstd(path)

    split_file(
        mono_path=f"{path}.zst", output_dir=OUTPUT_DIR, num_parts=10, compression_cmd="zstd"
    )
    imitate_translate(OUTPUT_DIR, suffix=".out")
    subprocess.run(
        ["pipeline/translate/collect.sh", OUTPUT_DIR, output_compressed, f"{path}.zst"], check=True
    )

    sh.zstd("-d", output_compressed)
    assert read_file(path) == read_file(output)


def test_split_collect_corpus(clean):
    os.environ["COMPRESSION_CMD"] = "zstd"
    length = 1234
    path_src = os.path.join(OUTPUT_DIR, "corpus.src.in")
    path_trg = os.path.join(OUTPUT_DIR, "corpus.trg.in")
    output = os.path.join(OUTPUT_DIR, "corpus.src.output")
    output_compressed = f"{output}.zst"
    generate_dataset(length, path_src)
    generate_dataset(length, path_trg)
    sh.zstd(path_src)
    sh.zstd(path_trg)

    split_file(
        mono_path=f"{path_src}.zst", output_dir=OUTPUT_DIR, num_parts=10, compression_cmd="zstd"
    )
    split_file(
        mono_path=f"{path_trg}.zst",
        output_dir=OUTPUT_DIR,
        num_parts=10,
        compression_cmd="zstd",
        output_suffix=".ref",
    )
    imitate_translate(OUTPUT_DIR, suffix=".nbest.out")
    subprocess.run(
        ["pipeline/translate/collect.sh", OUTPUT_DIR, output_compressed, f"{path_src}.zst"],
        check=True,
    )

    sh.zstd("-d", output_compressed)
    assert read_file(path_src) == read_file(output)

#!/usr/bin/env python3
"""
Downloads bicleaner-ai model for a lanuage pair.
Fallbacks to the multilingual model if the lanuage pair is not supported.

Example:
    python download_pack.py \
        --src=en \
        --trg=ru \
        --compression_cmd=zstd \
        artifacts/bicleaner-model-en-ru.zst
"""

import argparse
import os
import shutil
import subprocess
import tarfile
import tempfile
from typing import Optional


# bicleaner-ai-download downloads the latest models from Hugging Face / Github
# If a new model is released and you want to invalidate Taskcluster caches,
# change this file since it is a part of the cache digest
# The last model was added to https://huggingface.co/bitextor on Aug 29, 2023
def _run_download(src: str, trg: str, dir: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bicleaner-ai-download", trg, src, "full", dir], capture_output=True, check=False
    )


def _compress_dir(dir_path: str, compression_cmd: str) -> str:
    print(f"Compressing {dir_path}")
    if compression_cmd not in ["gzip", "zstd", "zstdmt", "pigz"]:
        raise ValueError(f"Unsupported compression tool {compression_cmd}.")

    tarball_path = f"{dir_path}.tar"
    with tarfile.open(tarball_path, "w") as tar:
        tar.add(dir_path, arcname=os.path.basename(dir_path))

    if compression_cmd in ("gzip", "pigz"):
        comp_ext = ".gz"
    else:
        comp_ext = ".zst"

    compressed_path = tarball_path + comp_ext
    subprocess.run([compression_cmd, tarball_path], check=True)

    return compressed_path


def check_result(result: subprocess.CompletedProcess):
    """Checks the return code, and outputs the stdout and stderr if it fails."""
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        result.check_returncode()


def download(src: str, trg: str, output_path: str, compression_cmd: str) -> None:
    tmp_dir = os.path.join(tempfile.gettempdir(), "bicleaner")
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)

    original_src = src
    original_trg = trg

    # Attempt to download a model.
    # 1: src-trg
    # 2: trg-src
    # 3: multilingual model
    print(f"Attempt 1 of 3: Downloading a model for {src}-{trg}")
    result = _run_download(src, trg, tmp_dir)

    pack_path = os.path.join(tmp_dir, f"{src}-{trg}")
    if os.path.exists(pack_path):
        check_result(result)
        print(f"The model for {src}-{trg} existed")
    else:
        src, trg = trg, src
        print(f"Attempt 2 of 3. Downloading a model for {src}-{trg}")
        result = _run_download(src, trg, tmp_dir)

        pack_path = os.path.join(tmp_dir, f"{src}-{trg}")

        if os.path.exists(pack_path):
            check_result(result)
            print(f"The model for {src}-{trg} existed")
        else:
            print("Attempt 3 of 3. Downloading the multilingual model en-xx")
            src = "en"
            trg = "xx"
            result = _run_download(src, trg, tmp_dir)

            pack_path = os.path.join(tmp_dir, f"{src}-{trg}")
            if not os.path.exists(pack_path):
                check_result(result)
                raise Exception("Could not download the multilingual model.")

    print("Compress the downloaded pack.")
    new_name = os.path.join(tmp_dir, f"bicleaner-ai-{original_src}-{original_trg}")
    print("pack_path: ", pack_path)
    print("new_name: ", new_name)

    if os.path.isdir(new_name):
        print("rmtree", new_name)
        shutil.rmtree(new_name)

    shutil.move(pack_path, new_name)
    pack_path = new_name
    if compression_cmd:
        pack_path = _compress_dir(pack_path, compression_cmd)

    # Move to the expected path
    print(f"Moving {pack_path} to {output_path}")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    shutil.move(pack_path, output_path)
    print("Done")


def main(args: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,  # Preserves whitespace in the help text.
    )
    parser.add_argument("--src", type=str, help="Source language code")
    parser.add_argument("--trg", type=str, help="Target language code")
    parser.add_argument(
        "--compression_cmd",
        type=str,
        help="Compression command (eg. pigz, zstd). "
        "Optional, if not provided the directory will not be compressed",
    )
    parser.add_argument(
        "output_path",
        type=str,
        help="Full output file or directory path for example artifacts/en-pt.zst",
    )

    parsed_args = parser.parse_args(args)

    download(
        src=parsed_args.src,
        trg=parsed_args.trg,
        output_path=parsed_args.output_path,
        compression_cmd=parsed_args.compression_cmd,
    )


if __name__ == "__main__":
    main()

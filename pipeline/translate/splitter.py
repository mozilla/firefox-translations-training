#!/usr/bin/env python3
"""
Splits a dataset to chunks. Generates files in format file.00.zst, file.01.zst etc.

Example:
    python splitter.py \
        --output_dir=test_data \
        --compression_cmd=zstd \
        --num_parts=10 \
        --output_suffix=.ref \
        test_data/corpus.en.zst
"""

import argparse
import os
import subprocess
from contextlib import ExitStack
from typing import Optional


def compress(compression_cmd: str, file_path: str):
    print(f"Compressing {file_path} with {compression_cmd}")
    subprocess.run([compression_cmd, file_path], check=True)

    # gzip and pigz remove the file by default, but zstd does not.
    if os.path.isfile(file_path):
        os.remove(file_path)


def split_file(
    mono_path: str, output_dir: str, num_parts: int, compression_cmd: str, output_suffix: str = ""
):
    os.makedirs(output_dir, exist_ok=True)

    # Initialize the decompression command
    decompress_cmd = f"{compression_cmd} -dc {mono_path}"

    # Use ExitStack to manage the cleanup of file handlers
    with ExitStack() as stack:
        decompressed = stack.enter_context(
            subprocess.Popen(decompress_cmd, shell=True, stdout=subprocess.PIPE)
        )
        total_lines = sum(1 for _ in decompressed.stdout)
        lines_per_part = (total_lines + num_parts - 1) // num_parts

        print(f"Splitting {mono_path} to {num_parts} chunks x {total_lines} lines")

        # Reset the decompression for actual processing
        decompressed = stack.enter_context(
            subprocess.Popen(decompress_cmd, shell=True, stdout=subprocess.PIPE)
        )
        current_file = None
        current_name = None
        current_line_count = 0
        file_index = 1

        for line in decompressed.stdout:
            # If the current file is full or doesn't exist, start a new one
            if current_line_count == 0 or current_line_count >= lines_per_part:
                if current_file is not None:
                    current_file.close()
                    compress(compression_cmd, current_name)

                current_name = f"{output_dir}/file.{file_index}{output_suffix}"
                current_file = stack.enter_context(open(current_name, "w"))
                print(f"A new file {current_name} created")
                file_index += 1
                current_line_count = 0

            current_file.write(line.decode())
            current_line_count += 1

    # decompress the last file after closing
    compress(compression_cmd, current_name)

    print("Done")


def main(args: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,  # Preserves whitespace in the help text.
    )
    parser.add_argument("mono_path", type=str, help="Path to the compressed monolingual dataset")
    parser.add_argument("--output_dir", type=str, help="Output directory to store split files")
    parser.add_argument("--num_parts", type=int, help="Number of parts to split the file into")
    parser.add_argument(
        "--compression_cmd", type=str, help="Compression command (e.g., pigz, gzip, zstd)"
    )
    parser.add_argument(
        "--output_suffix", type=str, help="A suffix for output files, for example .ref", default=""
    )

    parsed_args = parser.parse_args(args)

    split_file(
        mono_path=parsed_args.mono_path,
        output_dir=parsed_args.output_dir,
        num_parts=parsed_args.num_parts,
        compression_cmd=parsed_args.compression_cmd,
        output_suffix=parsed_args.output_suffix,
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Splits a dataset to chunks. Generates files in format file.00.zst, file.01.zst etc.

Example:
    python splitter.py \
        --output_dir=test_data \
        --num_parts=10 \
        --output_suffix=.ref \
        test_data/corpus.en.zst
"""

import argparse
import os
from contextlib import ExitStack
from typing import Optional

from pipeline.common.downloads import count_lines, read_lines, write_lines
from pipeline.common.logging import get_logger

logger = get_logger(__file__)


def split_file(mono_path: str, output_dir: str, num_parts: int, output_suffix: str = ""):
    """
    Split a file into fixed number of chunks.

    For instance with:

        mono_path     = "corpus.en.zst"
        output_dir    = "artifacts"
        num_parts     = 20
        output_suffix = ".ref"

    Outputs:
        .
        ├── corpus.en.zst
        └── artifacts
            ├── file.1.ref.zst
            ├── file.2.ref.zst
            ├── file.3.ref.zst
            ├── ...
            └── file.20.ref.zst
    """
    os.makedirs(output_dir, exist_ok=True)

    total_lines = count_lines(mono_path)
    lines_per_part = (total_lines + num_parts - 1) // num_parts
    logger.info(f"Splitting {mono_path} to {num_parts} chunks x {total_lines:,} lines")

    line_writer = None
    line_count = 0
    file_index = 1

    with read_lines(mono_path) as lines:
        with ExitStack() as chunk_stack:
            for line in lines:
                if not line_writer or line_count >= lines_per_part:
                    # The current file is full or doesn't exist, start a new one.
                    if line_writer:
                        chunk_stack.close()

                    chunk_name = f"{output_dir}/file.{file_index}{output_suffix}.zst"
                    logger.info(f"Writing to file chunk: {chunk_name}")
                    line_writer = chunk_stack.enter_context(write_lines(chunk_name))
                    file_index += 1
                    line_count = 0

                line_writer.write(line)
                line_count += 1

    logger.info("Done writing to files.")


def main(args: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,  # Preserves whitespace in the help text.
    )
    parser.add_argument("mono_path", type=str, help="Path to the compressed monolingual dataset")
    parser.add_argument("--output_dir", type=str, help="Output directory to store split files")
    parser.add_argument("--num_parts", type=int, help="Number of parts to split the file into")
    parser.add_argument(
        "--output_suffix", type=str, help="A suffix for output files, for example .ref", default=""
    )

    parsed_args = parser.parse_args(args)

    split_file(
        mono_path=parsed_args.mono_path,
        output_dir=parsed_args.output_dir,
        num_parts=parsed_args.num_parts,
        output_suffix=parsed_args.output_suffix,
    )


if __name__ == "__main__":
    main()

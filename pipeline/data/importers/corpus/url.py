#!/usr/bin/env python3
"""
Import data from a url.

Example usage:

pipeline/data/importers/corpus/url.py                                                       \\
  en                                                                       `# src`           \\
  ru                                                                       `# trg`           \\
  artifacts/releng-translations-dev_data_custom-en-ru_zip                  `# output_prefix` \\
  https://storage.google.com/releng-translations-dev/data/custom-en-ru.zip `# url`
"""

import argparse

from pipeline.common.downloads import stream_download_to_file
from pipeline.common.logging import get_logger

logger = get_logger(__file__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,  # Preserves whitespace in the help text.
    )
    parser.add_argument("src", type=str)
    parser.add_argument("trg", type=str)
    parser.add_argument("output_prefix", type=str)
    parser.add_argument("url", type=str)

    args = parser.parse_args()

    src_file = args.url.replace("[LANG]", args.src)
    trg_file = args.url.replace("[LANG]", args.trg)
    src_dest = f"{args.output_prefix}.{args.src}.zst"
    trg_dest = f"{args.output_prefix}.{args.trg}.zst"

    logger.info(f"src:           {args.src}")
    logger.info(f"trg:           {args.trg}")
    logger.info(f"output_prefix: {args.output_prefix}")
    logger.info(f"src_dest:      {src_dest}")
    logger.info(f"trg_dest:      {trg_dest}")

    stream_download_to_file(src_file, src_dest)
    stream_download_to_file(trg_file, trg_dest)


if __name__ == "__main__":
    main()

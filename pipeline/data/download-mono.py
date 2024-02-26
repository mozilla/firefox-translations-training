#!/usr/bin/env python3
"""
Downloads a monolingual dataset, shuffles it, and truncates it to a maximum amount of sentences.

Kinds:
   taskcluster/kinds/dataset/kind.yml

Example usage:

    pipeline/data/download-mono.py                  \\
        --dataset news-crawl_news.2021              \\
        --language en                               \\
        --max_sentences 100000000                   \\
        --artifacts $TASK_WORKDIR/artifacts

Artifacts:

    artifacts
    └── news.2021.en.zst
"""

import argparse
import os
from typing import Optional

import zstandard

from pipeline.common.datasets import Dataset, shuffle_with_max_lines
from pipeline.common.downloads import (
    RemoteGzipLineStreamer,
    RemoteZstdLineStreamer,
    get_download_size,
)
from pipeline.common.logging import get_logger

# TODO(CJK) - Issue #424
MAX_WORDS_IN_SENTENCE = 100

CURRENT_FOLDER = os.path.dirname(os.path.abspath(__file__))
IMPORTERS_PATH = os.path.abspath(os.path.join(CURRENT_FOLDER, "mono"))

logger = get_logger(__file__)


def main(args_list: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,  # Preserves whitespace in the help text.
    )
    parser.add_argument("--dataset", type=str, help="The key for the dataset")
    parser.add_argument("--language", type=str, help="The BCP 47 language tag of the dataset")
    parser.add_argument(
        "--max_sentences", type=int, help="The maximum number of sentences to retain"
    )
    parser.add_argument(
        "--artifacts", type=str, help="The location where the dataset will be saved"
    )
    args = parser.parse_args(args_list)

    dataset = Dataset(args.dataset)

    file_destination = os.path.join(
        args.artifacts, f"{dataset.file_safe_name()}.{args.language}.zst"
    )

    logger.info(f"Dataset: {args.dataset}")
    logger.info(f"Language: {args.language}")
    logger.info(f"Max Sentences: {args.max_sentences}")
    logger.info(f"Artifacts: {args.artifacts}")
    logger.info(f"File Destination: {file_destination}")

    if not os.path.exists(args.artifacts):
        os.makedirs(args.artifacts)

    line_streamer = None
    url = None
    if dataset.importer == "url":
        dataset = Dataset(args.dataset)
        url = dataset.name
        line_streamer = RemoteZstdLineStreamer(url)
    elif dataset.importer == "news-crawl":
        url = f"http://data.statmt.org/news-crawl/{args.language}/{dataset.name}.{args.language}.shuffled.deduped.gz"
        logger.info("Downloading WMT newscrawl monolingual data")
        logger.info(url)
        line_streamer = RemoteGzipLineStreamer(url)
    else:
        raise Exception(f'Unsupported importer "{dataset.importer}"')

    logger.info(f"URL: {url}")

    with zstandard.open(file_destination, "wb") as zst_file, line_streamer as line_stream:
        for line in shuffle_with_max_lines(
            line_stream=line_stream,
            seed=dataset.name,
            max_lines=args.max_sentences,
            max_words_in_sentence=100,
            total_byte_size=get_download_size(url),
        ):
            zst_file.write(line.encode("utf-8"))


if __name__ == "__main__":
    main()

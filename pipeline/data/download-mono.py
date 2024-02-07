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
import gzip
import io
import os
import re
from random import Random
from typing import Iterator, Optional

import requests
import zstandard
from google.cloud.storage.fileio import BlobReader

from pipeline.utils import Dataset, attempt_mocked_request
from pipeline.utils.downloads import google_cloud_storage
from pipeline.utils.logging import get_logger

# TODO(CJK) - Issue #424
MAX_WORDS_IN_SENTENCE = 100

CURRENT_FOLDER = os.path.dirname(os.path.abspath(__file__))
IMPORTERS_PATH = os.path.abspath(os.path.join(CURRENT_FOLDER, "mono"))

logger = get_logger("download_mono")


def shuffle_and_truncate(
    line_stream: Iterator[str], dataset: Dataset, file_destination: str, max_sentences: int
):
    lines: list[str] = []

    logger.info("Load the stream into memory, discarding sentences that are too long.")
    for line in line_stream:
        if len(line.split()) < MAX_WORDS_IN_SENTENCE:
            lines.append(line)

    logger.info("Perform an in-memory shuffle of the dataset.")
    random = Random(dataset.key)  # Make this deterministic based on dataset key.
    random.shuffle(lines)

    logger.info("Write out the lines, truncated to the max number of sentences.")
    with open(file_destination, "wb") as compressed_file:
        with zstandard.ZstdCompressor().stream_writer(compressed_file) as writer:
            for line in lines[:max_sentences]:
                # The newline is already included.
                writer.write(line.encode("utf-8"))


def parse_bucket_from_dataset_key(dataset_key: str):
    # bucket_releng-translations-dev/data/custom-en-ru.zip
    matches = re.search(r"^bucket_([\w-]*)/(.*)$", dataset_key)
    if not matches:
        raise Exception(f"Could not parse the name {dataset_key}")

    bucket_name = matches.group(1)
    file_path = matches.group(2)

    return bucket_name, file_path


class BucketZSTLineStreamer:
    """Stream lines directly from a .zst file in Google Cloud Storage."""

    def __init__(self, bucket_name: str, bucket_path: str) -> None:
        super().__init__()
        self.bucket_name = bucket_name
        self.bucket_path = bucket_path

        self.network_stream = None
        self.decoding_stream = None
        self.line_stream = None

    def __enter__(self):
        logger.info(f"Bucket Name: {self.bucket_name}")
        logger.info(f"Bucket Path: {self.bucket_path}")

        client = google_cloud_storage.Client.create_anonymous_client()
        bucket = client.bucket(self.bucket_name)

        self.network_stream = BlobReader(bucket.blob(self.bucket_path))
        self.decoding_stream = zstandard.ZstdDecompressor().stream_reader(self.network_stream)
        self.line_stream = io.TextIOWrapper(self.decoding_stream, encoding="utf-8")

        return self.line_stream

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        self.line_stream.close()
        self.decoding_stream.close()
        self.network_stream.close()


class RemoteGzipLineStreamer:
    """Stream lines directly from a remote gzip file."""

    def __init__(self, url: str) -> None:
        self.url = url

        self.decoding_stream = None
        self.response = None
        self.line_stream = None

    def __enter__(self):
        mocked_stream = attempt_mocked_request(self.url)
        if mocked_stream:
            # We are in a test.
            logger.info(f"Using a mocked download: {self.url}")
            self.response = mocked_stream
        else:
            self.response = requests.get(self.url, stream=True)
            self.response.raise_for_status()

        self.decoding_stream = gzip.GzipFile(fileobj=self.response.raw)
        self.line_stream = io.TextIOWrapper(self.decoding_stream, encoding="utf-8")
        return self.line_stream

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        self.line_stream.close()
        self.decoding_stream.close()
        self.response.close()


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
        args.artifacts, f"{dataset.file_safe_name}.{args.language}.zst"
    )

    logger.info(f"Dataset: {args.dataset}")
    logger.info(f"Language: {args.language}")
    logger.info(f"Max Sentences: {args.max_sentences}")
    logger.info(f"Artifacts: {args.artifacts}")
    logger.info(f"File Destination: {file_destination}")

    if not os.path.exists(args.artifacts):
        os.makedirs(args.artifacts)

    line_streamer = None
    if dataset.importer == "bucket":
        bucket_name, file_path = parse_bucket_from_dataset_key(args.dataset)
        bucket_path = f"{file_path}.{args.language}.zst"
        line_streamer = BucketZSTLineStreamer(bucket_name, bucket_path)
    elif dataset.importer == "news-crawl":
        url = f"http://data.statmt.org/news-crawl/{args.language}/{dataset.name}.{args.language}.shuffled.deduped.gz"
        logger.info("Downloading WMT newscrawl monolingual data")
        logger.info(url)
        line_streamer = RemoteGzipLineStreamer(url)
    else:
        raise Exception(f'Unsupported importer "{dataset.importer}"')

    with line_streamer as line_stream:
        shuffle_and_truncate(line_stream, dataset, file_destination, args.max_sentences)


if __name__ == "__main__":
    main()

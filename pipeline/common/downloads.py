import gzip
import io
import json
import os
from io import BufferedReader
from typing import Optional

import requests
import zstandard

from pipeline.common.logging import get_logger

logger = get_logger(__file__)


def stream_download_to_file(url: str, destination: str) -> None:
    """
    Streams a download to a file using 1mb chunks.
    """
    response = requests.get(url, stream=True)
    if not response.ok:
        raise Exception(f"Unable to download file from {url}")
    with open(destination, "wb") as f:
        logger.info("Streaming downloading: {url}")
        logger.info("To: {destination}")
        # Stream to disk in 1 megabyte chunks.
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            f.write(chunk)


class MockedResponse:
    def __init__(self, file_handle: BufferedReader) -> None:
        self.raw = file_handle

    def close(self) -> None:
        self.raw.close()


def get_mocked_downloads_file_path(url: str) -> Optional[str]:
    """If there is a mocked download, get the path to the file, otherwise return None"""
    if not os.environ.get("MOCKED_DOWNLOADS"):
        return None

    mocked_downloads = json.loads(os.environ.get("MOCKED_DOWNLOADS"))

    if not isinstance(mocked_downloads, dict):
        raise Exception(
            "Expected the mocked downloads to be a json object mapping the URL to file path"
        )

    source_file = mocked_downloads.get(url)
    if not source_file:
        print("MOCKED_DOWNLOADS:", mocked_downloads)
        raise Exception(f"Received a URL that was not in MOCKED_DOWNLOADS {url}")

    if not os.path.exists(source_file):
        raise Exception(f"The source file specified did not exist {source_file}")

    logger.info("Mocking a download.")
    logger.info(f"   url: {url}")
    logger.info(f"  file: {source_file}")

    return source_file


def attempt_mocked_request(url: str) -> Optional[requests.Response]:
    """
    If there are mocked download, use that.
    """
    file_path = get_mocked_downloads_file_path(url)
    if file_path:
        return MockedResponse(open(file_path, "rb"))
    return None


def get_download_size(url: str) -> int:
    """Get the total bytes of a file to download."""
    mocked_file_path = get_mocked_downloads_file_path(url)
    if mocked_file_path:
        return os.path.getsize(mocked_file_path)

    response = requests.head(url, allow_redirects=True)
    size = response.headers.get("content-length", 0)
    return int(size)


class RemoteDecodingLineStreamer:
    """Stream lines directly from a remote compressed file."""

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

        self.decoding_stream = self.decode(self.response.raw)
        self.line_stream = io.TextIOWrapper(self.decoding_stream, encoding="utf-8")
        return self.line_stream

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        self.line_stream.close()
        self.decoding_stream.close()
        self.response.close()

    def decode(self):
        raise NotImplementedError


class RemoteGzipLineStreamer(RemoteDecodingLineStreamer):
    """Stream lines directly from a remote gzip file."""

    def decode(self, response_stream):
        return gzip.GzipFile(fileobj=response_stream)


class RemoteZstdLineStreamer(RemoteDecodingLineStreamer):
    """Stream lines directly from a remote zstd file."""

    def decode(self, response_stream):
        return zstandard.ZstdDecompressor().stream_reader(response_stream)

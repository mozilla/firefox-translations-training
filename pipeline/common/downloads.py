import gzip
import io
import json
import os
import time
from io import BufferedReader
from typing import Generator, Optional

import requests
import zstandard

from pipeline.common.logging import get_logger

logger = get_logger(__file__)


def stream_download_to_file(url: str, destination: str) -> None:
    """
    Streams a download to a file, and retries several times if there are any failures. The
    destination file must not already exist.
    """
    if os.path.exists(destination):
        raise Exception(f"That file already exists: {destination}")

    logger.info(f"Destination: {destination}")

    with open(destination, "wb") as file, DownloadChunkStreamer(url) as chunk_streamer:
        for chunk in chunk_streamer.download_chunks():
            file.write(chunk)


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


def attempt_mocked_request(url: str) -> Optional[BufferedReader]:
    """
    If there are mocked download, use that.
    """
    file_path = get_mocked_downloads_file_path(url)
    if file_path:
        return open(file_path, "rb")
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
    """
    Base class to stream lines directly from a remote file.
    """

    def __init__(self, url: str) -> None:
        self.url = url

        self.decoding_stream = None
        self.byte_chunk_stream = None
        self.line_stream = None

    def __enter__(self):
        mocked_request = attempt_mocked_request(self.url)
        if mocked_request:
            # We are in a test.
            logger.info(f"Using a mocked download: {self.url}")
            self.byte_chunk_stream = mocked_request
            self.decoding_stream = self.decode(self.byte_chunk_stream)
        else:
            self.byte_chunk_stream = DownloadChunkStreamer(self.url).__enter__()
            self.decoding_stream = self.decode(self.byte_chunk_stream)

        self.line_stream = io.TextIOWrapper(self.decoding_stream, encoding="utf-8")

        return self.line_stream

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        self.line_stream.close()
        self.decoding_stream.close()
        self.byte_chunk_stream.close()

    def decode(self, byte_stream):
        raise NotImplementedError("Decoding is not implemented")


class RemoteGzipLineStreamer(RemoteDecodingLineStreamer):
    """
    Stream lines directly from a remote gzip file. The line includes the newlines separator.

    Usage:

        with RemoteGzipLineStreamer(url) as lines:
            for line in lines:
                print(line)
    """

    def decode(self, byte_stream):
        return gzip.GzipFile(fileobj=byte_stream)


class RemoteZstdLineStreamer(RemoteDecodingLineStreamer):
    """
    Stream lines directly from a remote zstd file. The line includes the newlines separator.

    Usage:

        with RemoteZstdLineStreamer(url) as lines:
            for line in lines:
                print(line)
    """

    def decode(self, byte_stream):
        return zstandard.ZstdDecompressor().stream_reader(byte_stream)


class DownloadChunkStreamer(io.IOBase):
    """
    Streams a download as chunks, and retries several times if there are any failures. This
    clas implements io.IOBase so it can be used as a file reader.

    Iterator over chunks directly:

        with DownloadChunkStreamer(url) as chunk_streamer:
            for chunk in chunk_streamer.download_chunks():
                f.write(chunk)

    Or pass it as a file handle:

        with DownloadChunkStreamer(url) as f:
             gzip.GzipFile(fileobj=f)
    """

    def __init__(self, url: str, total_retries=3, timeout_sec=10.0, wait_before_retry_sec=60.0):
        self.url = url
        self.response = None

        # How many retry attempts should there be, and how long to wait between retries.
        self.total_retries = total_retries
        self.wait_before_retry_sec = wait_before_retry_sec

        # How long to wait for a response to timeout? This is the time that no new data is received.
        self.timeout_sec = timeout_sec

        self.report_every = 0.05  # What percentage of the download to report updates?
        self.next_report_percent = self.report_every  # The next report percentage.

        self.downloaded_bytes = 0
        self.chunk_bytes = 8 * 1024

        # The buffered `read` data.
        self.buffer = b""

        # The Generator result of _download_chunks.
        self.chunk_iter: Optional[Generator[bytes, None, None]] = None

    def __enter__(self):
        """
        On enter, kick off the download, and store the chunk iterator. This iterator
        handles the restarts for Requests.
        """
        self.chunk_iter = self.download_chunks()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """
        Close out the response, and cancel any iterators.
        """
        if self.response:
            self.response.close()

        self.response = None
        self.chunk_iter = None

    def read(self, size=-1) -> bytes:
        """
        This method implements the io.IOBase read method. It buffers the chunks until the `size`
        requirement is fulfilled. It is backed by the chunks_iter created by the download_chunks
        method.
        """
        if not self.chunk_iter:
            # The chunk iterator was consumed. Return an empty byte object to indicate the download
            # is complete.
            return b""

        if size < 0:
            # Load everything into the buffer, and return it.
            for chunk in self.chunk_iter:
                self.buffer += chunk
            result = self.buffer
            self.buffer = b""
            return result

        # Load the buffer with requested amount of data to read. -1 indicates load everything.
        while len(self.buffer) < size:
            chunk = next(self.chunk_iter, None)
            if chunk:
                self.buffer += chunk
            else:
                # The stream ended.
                break

        # Return the requested read amount, and divide up the remaining buffer.
        result = self.buffer[:size]
        self.buffer = self.buffer[size:]

        return result

    def download_chunks(self) -> Generator[bytes, None, None]:
        """
        This method is the generator that is responsible for running the request, and retrying
        when there is a failure. It yields the fixed size byte chunks, and exposes a generator
        to be consumed. This generator can be used directly in a for loop, or the entire class
        can be passed in as a file handle.
        """
        next_report_percent = self.report_every
        total_bytes = 0

        for retry in range(self.total_retries):
            if retry > 0:
                logger.error(f"Remaining retries: {self.total_retries - retry}")

            try:
                headers = {}
                if self.downloaded_bytes > 0:
                    # Pick up the download from where it was before.
                    headers = {"Range": f"bytes={self.downloaded_bytes}-"}

                self.response = requests.get(
                    self.url, headers=headers, stream=True, timeout=self.timeout_sec
                )
                self.response.raise_for_status()

                # Report the download size.
                if not total_bytes and "content-length" in self.response.headers:
                    total_bytes = int(self.response.headers["content-length"])
                    logger.info(f"Download size: {total_bytes} bytes")

                for chunk in self.response.iter_content(chunk_size=self.chunk_bytes):
                    if not chunk:
                        continue

                    self.downloaded_bytes += len(chunk)

                    # Report the percentage downloaded every `report_every` percentage.
                    if total_bytes and self.downloaded_bytes >= next_report_percent * total_bytes:
                        logger.info(
                            f"{self.downloaded_bytes / total_bytes * 100.0:.0f}% downloaded "
                            f"({self.downloaded_bytes}/{total_bytes} bytes)"
                        )
                        next_report_percent += self.report_every

                    yield chunk

                # The download is complete.
                self.close()
                logger.info("100% downloaded - Download finished.")
                return

            except requests.exceptions.Timeout as error:
                logger.error(f"The connection timed out: {error}.")

            except requests.exceptions.RequestException as error:
                # The RequestException is the generic error that catches all classes of "requests"
                # errors. Don't attempt to be be smart about this, just attempt again until
                # the retries are done.
                logger.error(f"A download error occurred: {error}")

            # Close out the response on an error. It will be recreated when retrying.
            if self.response:
                self.response.close()
                self.response = None

            logger.info(f"Retrying in {self.wait_before_retry_sec} sec")
            time.sleep(self.wait_before_retry_sec)

        self.close()
        raise Exception("The download failed.")

    def decode(self, byte_stream) -> Generator[bytes, None, None]:
        """Pass through the byte stream. This method can be specialized by child classes."""
        return byte_stream

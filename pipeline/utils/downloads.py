import io
import json
import os
import shutil

from google.api_core.exceptions import RequestRangeNotSatisfiable
from google.cloud import storage as RealStorage

from pipeline.utils.logging import get_logger

google_cloud_storage: RealStorage


# Use mocked downloads if they exist.
if os.environ.get("MOCKED_DOWNLOADS"):
    logger = get_logger("google_cloud(mocked)")

    class MockedBlob:
        name: str
        bucket: "MockedBucket"

        def __init__(self, name, bucket) -> None:
            super().__init__()
            self.name = name
            self.bucket = bucket
            self.chunk_size = 1024**2
            self._downloaded = False

        def _get_mocked_source_file(self) -> str:
            if not os.environ.get("MOCKED_DOWNLOADS"):
                raise Exception(
                    "The mocked google cloud storage utility expected the MOCKED_DOWNLOADS environment variable to be set."
                )
            mocked_downloads = json.loads(os.environ.get("MOCKED_DOWNLOADS"))

            if not isinstance(mocked_downloads, dict):
                raise Exception(
                    "Expected the mocked downloads to be a json object mapping the URL to file path"
                )
            url = f"gs://{self.bucket.name}/{self.name}"
            source_file: str = mocked_downloads.get(url)
            if not source_file:
                logger.info(f"MOCKED_DOWNLOADS: {mocked_downloads}")
                raise Exception(f"Received a URL that was not in MOCKED_DOWNLOADS {url}")

            if not os.path.exists(source_file):
                raise Exception(f"The source file specified did not exist {source_file}")

            return source_file

        def download_as_bytes(self, start=None, end=None, checksum=None, retry=None) -> bytes:
            if self._downloaded:
                raise RequestRangeNotSatisfiable("Done")
            self._downloaded = True

            with open(self._get_mocked_source_file(), "rb") as file:
                bytes = io.BytesIO(file.read())
                return bytes.getvalue()

        def download_to_filename(self, destination_path: str) -> None:
            source_file = self._get_mocked_source_file()

            logger.info("copying the file")
            logger.info(f"from: {source_file}")
            logger.info(f"to: {destination_path}")

            shutil.copyfile(source_file, destination_path)
            logger.info(f"Source file: {os.stat(source_file).st_size} bytes")
            logger.info(f"Target file: {os.stat(destination_path).st_size} bytes")

    class MockedBucket:
        def __init__(self, name: str) -> None:
            self.name = name

        def blob(self, name: str):
            return MockedBlob(name, bucket=self)

    class MockedClient:
        @staticmethod
        def create_anonymous_client():
            return MockedClient()

        def bucket(self, bucket_name: str):
            return MockedBucket(bucket_name)

    class MockedStorage:
        Client = MockedClient

    google_cloud_storage = MockedStorage()
else:
    google_cloud_storage = RealStorage
    # requests =

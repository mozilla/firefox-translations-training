#!/usr/bin/env python3
"""
Import data from a Google Cloud storage bucket.

Example usage:

pipeline/data/importers/corpus/bucket.py \
  en                                                       `# src`
  ru                                                       `# trg`
  $artifacts/releng-translations-dev_data_custom-en-ru_zip `# output_prefix`
  releng-translations-dev/data/custom-en-ru.zip            `# name`
"""

import argparse
import re

from pipeline.utils.downloads import google_cloud_storage


def parse_name(name: str):
    # releng-translations-dev/data/custom-en-ru.zip
    matches = re.search(r"^([\w-]*)/(.*)$", name)
    if not matches:
        raise Exception(f"Could not parse the name {name}")

    bucket_name = matches.group(1)
    file_path = matches.group(2)

    return bucket_name, file_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,  # Preserves whitespace in the help text.
    )
    parser.add_argument("src", type=str)
    parser.add_argument("trg", type=str)
    parser.add_argument("output_prefix", type=str)
    parser.add_argument("name", type=str)

    args = parser.parse_args()

    bucket_name, file_path = parse_name(args.name)

    print("src", args.src)
    print("trg", args.trg)
    print("output_prefix", args.output_prefix)
    print("name", args.name)
    print("bucket_name", bucket_name)
    print("file_path", f"{file_path}.{args.src}.zst")
    print("file_path", f"{file_path}.{args.trg}.zst")

    src_file = f"{file_path}.{args.src}.zst"
    trg_file = f"{file_path}.{args.trg}.zst"
    src_dest = f"{args.output_prefix}.{args.src}.zst"
    trg_dest = f"{args.output_prefix}.{args.trg}.zst"

    client = google_cloud_storage.Client.create_anonymous_client()
    bucket = client.bucket(bucket_name)

    print("Bucket:", bucket_name)
    print("Downloading:", src_file)
    bucket.blob(src_file).download_to_filename(src_dest)
    print("Downloading:", src_file)
    bucket.blob(trg_file).download_to_filename(trg_dest)


if __name__ == "__main__":
    main()

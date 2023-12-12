#!/usr/bin/env python3
"""
Finds all opus datasets for a language pair and prints them to set config settings.

Usage:
    poetry install --only utils
    poetry run ./utils/find_corpus.py "en" "ca"
    poetry run ./utils/find_corpus.py "en" "fr" --importer opus
"""

import argparse
import logging
import sys
from typing import NamedTuple, Optional, TypeVar, Union

import humanize
import requests


class OpusDataset(NamedTuple):
    # The name of this dataset, e.g. "CCAligned"
    corpus: str
    # This is a blank string at the time of this writing.
    documents: str

    # 'moses'
    preprocessing: str
    # The language tag.
    source: str
    # The language tag.
    target: str
    # The URL to the download
    url: str
    # For example "v1"
    version: str

    alignment_pairs: int
    id: int
    # Size in KiB
    size: int
    source_tokens: int
    target_tokens: int

    latest: Union["True", "False"]

    def name(self) -> str:
        return f"opus_{self.corpus}/{self.version}"

    def website_url(self) -> str:
        return f"https://opus.nlpl.eu/{self.corpus}-{self.version}.php"

    def humanize_size(self) -> str:
        return humanize.naturalsize(self.size * 1024)


def get_opus(source: str, target: str, download_url: bool):
    # This API is documented: https://opus.nlpl.eu/opusapi/
    url = f"https://opus.nlpl.eu/opusapi/?source={source}&target={target}&preprocessing=moses&version=latest"

    print(f"Fetching datasets from:\n{url}\n")

    datasets = requests.get(url).json()

    # Convert the response into a typed object that is sorted.
    datasets_typed = [OpusDataset(**corpus_data) for corpus_data in datasets.get("corpora", [])]
    datasets_typed = sorted(datasets_typed, key=lambda x: x.alignment_pairs or 0, reverse=True)

    print("")
    print("┌──────────────────────────────┐")
    print("│ OPUS - https://opus.nlpl.eu/ │")
    print("└──────────────────────────────┘")

    print_table(
        [
            [
                "Dataset",
                "Code",
                "Sentences",
                "Size",
                "URL",
            ],
            *[
                [
                    dataset.corpus,
                    dataset.name(),
                    dataset.alignment_pairs,
                    dataset.humanize_size(),
                    dataset.url if download_url else dataset.website_url(),
                ]
                for dataset in datasets_typed
            ],
        ]
    )

    names = [f'opus_{d["corpus"]}/{d["version"]}' for d in datasets["corpora"]]
    print_yaml(names, exclude=["OPUS100v", "WMT-News"])


def get_sacrebleu(source: str, target: str):
    import sacrebleu

    entries = [
        (name, entry)
        for name, entry in sacrebleu.DATASETS.items()
        if f"{source}-{target}" in entry or f"{target}-{source}" in entry
    ]

    names = [f"sacrebleu_{name}" for name, entry in entries]

    print("")
    print("┌─────────────────────────────────────────────────┐")
    print("│ sacrebleu - https://github.com/mjpost/sacrebleu │")
    print("└─────────────────────────────────────────────────┘")
    print_table(
        [
            ["Dataset", "Description", "URLs"],
            *[
                [
                    #
                    name,
                    entry["description"],
                    ", ".join(entry["data"]),
                ]
                for name, entry in entries
            ],
        ]
    )
    print_yaml(names)


def get_remote_file_size(url: str) -> Optional[int]:
    try:
        response = requests.head(url, timeout=1)

        if response.status_code == 200:
            return humanize.naturalsize(int(response.headers.get("Content-Length", 0)))
        else:
            print(f"Failed to retrieve file information. Status code: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None


T = TypeVar("T")


def exclude_by_name(excludes: list[str], names: list[str], entries: list[T]) -> list[T]:
    """Exclude entries by an excludes list, and a name list."""
    filtered_entries = []
    for name, entry in zip(names, entries):
        filter = False
        for exclude in excludes:
            if exclude.lower() in name.lower():
                filter = True
                break

        if not filter:
            filtered_entries.append(entry)

    return filtered_entries


def get_mtdata(source: str, target: str):
    # mtdata outputs debug logs
    logging.disable(logging.CRITICAL)

    from mtdata.entry import lang_pair
    from mtdata.index import get_entries
    from mtdata.iso import iso3_code

    source_tricode = iso3_code(source, fail_error=True)
    target_tricode = iso3_code(target, fail_error=True)
    entries = sorted(
        get_entries(lang_pair(source_tricode + "-" + target_tricode), None, None, True),
        key=lambda entry: entry.did.group,
    )
    excludes = ["opus", "newstest", "UNv1"]

    def get_name(entry):
        return (
            f"mtdata_{entry.did.group}-{entry.did.name}-{entry.did.version}-{entry.did.lang_str}"
        )

    names = [get_name(entry) for entry in entries]

    print("")
    print("┌────────────────────────────────────────────────┐")
    print("│ mtdata - https://github.com/thammegowda/mtdata │")
    print("└────────────────────────────────────────────────┘")
    print_table(
        [
            [
                "Dataset",
                "URL",
                # "Size",
            ],
            *[
                [
                    #
                    get_name(entry),
                    entry.url,
                    # get_remote_file_size(entry.url),
                ]
                for entry in
                # Filter out the excludes
                exclude_by_name(excludes, names, entries)
            ],
        ]
    )

    print_yaml(names, exclude=excludes)


def print_yaml(names: list[str], exclude: list[str] = []):
    cleaned = set()
    for name in names:
        filter = False
        for ex in exclude:
            if ex.lower() in name.lower():
                filter = True
                break
        if not filter:
            cleaned.add(name)

    print("\nYAML:")
    if len(cleaned) == 0:
        print("(no datasets)\n")
    else:
        print("\n".join(sorted([f"    - {name}" for name in cleaned])))


def run(source: str, target: str, importer: Optional[str]):
    if importer == "opus" or not type:
        get_opus(source, target)

    if importer == "sacrebleu" or not type:
        get_sacrebleu(source, target)

    if importer == "mtdata" or not type:
        get_mtdata(source, target)


def print_table(table: list[list[any]]):
    """
    Nicely print a table, the first row is the header
    """

    # Compute the column lengths.
    transposed_table = list(map(list, zip(*table)))
    column_lengths = [max(len(str(x)) for x in column) for column in transposed_table]

    print("")
    for index, row in enumerate(table):
        # Print the row.
        for datum, max_len in zip(row, column_lengths):
            print(str(datum).ljust(max_len), end=" ")
        print("")

        # Print a separator between the header and the rest of the table.
        if index == 0:
            for length in column_lengths:
                print("".ljust(length, "─"), end=" ")
            print("")

    if len(table) == 1:
        print("(no datasets)")


def main(args: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,  # Preserves whitespace in the help text.
    )
    parser.add_argument("source", type=str, nargs="?", help="Source language code")
    parser.add_argument("target", type=str, nargs="?", help="Target language code")
    parser.add_argument(
        "--importer", type=str, help="The importer to use: mtdata, opus, sacrebleu"
    )
    parser.add_argument(
        "--download_url",
        action="store_true",
        default=False,
        help="Show the download url if available.",
    )

    args = parser.parse_args(args)

    if not args.source or not args.target:
        parser.print_help()
        sys.exit(1)

    if args.importer and args.importer not in ["opus", "sacrebleu", "mtdata"]:
        print(f'"{args.importer}" is not a valid importer.')
        sys.exit(1)

    if args.importer == "opus" or not args.importer:
        get_opus(args.source, args.target, args.download_url)

    if args.importer == "sacrebleu" or not args.importer:
        get_sacrebleu(args.source, args.target)

    if args.importer == "mtdata" or not args.importer:
        get_mtdata(args.source, args.target)


if __name__ == "__main__":
    main()

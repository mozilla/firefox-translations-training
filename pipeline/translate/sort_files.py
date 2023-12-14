#!/usr/bin/env python3
"""
Finds and sorts translation part files

Example:
    python sort_files.py --dir=fetches
"""

import argparse
import os
import re


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir")
    args = parser.parse_args()
    dir = args.dir

    # nbest for corpus output
    regex = re.compile(r'file\.(\d+)\.(nbest\.)?out$')

    def extract_number(filename):
        match = regex.search(filename)
        return int(match.group(1)) if match else None

    # List and sort the files based on the extracted number
    sorted_files = sorted(
        (f for f in os.listdir(dir) if regex.search(f)),
        key=extract_number
    )

    # Print or process the sorted files
    for file in sorted_files:
        print(os.path.join(dir, file))


if __name__ == "__main__":
    main()

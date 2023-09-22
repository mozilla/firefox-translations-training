"""
Generates filter config for a dataset based on defaults to use in OpusCleaner
"""

import argparse
import json
import os
from typing import Dict, Optional


def find_custom_filter(src, trg, dataset) -> Optional[Dict]:
    # TODO: we'll likely need to move to a separate repo for those
    # TODO: to not include all filters for all languages in TC artifacts

    # workaround: we use "_" to separate the dataset version for OPUS datasets and OpusCleaner uses "-"
    idx = dataset.rfind("_")
    dataset_opus = f"{dataset[:idx]}-{dataset[idx + 1:]}" if idx else ""

    paths = [
        f"configs/{src}-{trg}/{dataset}.{src}-{trg}.filters.json",
        f"configs/{trg}-{src}/{dataset}.{trg}-{src}.filters.json",
        f"configs/{trg}-{src}/{dataset_opus}.{trg}-{src}.filters.json",
        f"configs/{src}-{trg}/{dataset_opus}.{src}-{trg}.filters.json",
    ]

    for path in paths:
        if os.path.exists(path):
            with open(path) as f:
                config = json.load(f)
                print(f"Found custom filter {path}")
                return config

    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input_prefix", metavar="INPUT_PREFIX", type=str, help="Dataset file prefix"
    )
    parser.add_argument("src", metavar="SRC", type=str, help="Source language code")
    parser.add_argument("trg", metavar="TRG", type=str, help="Target language code")
    parser.add_argument("dataset", metavar="DATASET", type=str, help="Dataset name")
    parser.add_argument("output", metavar="OUTPUT_PATH", type=str, help="Write filter config here")

    args = parser.parse_args()
    src = args.src
    trg = args.trg
    dataset = args.dataset
    output = args.output

    # look whether there are custom filters produced by OpusCleaner UI first
    config = find_custom_filter(src, trg, dataset)
    if config:
        print("Using custom filter")
    else:
        # if a custom filter is not found, use defaults
        # note: do not call the folder with default filters "filters" because it's a magic word for opuscleaner-clean
        # and it starts processing such folder
        # TODO: ideally "other" for "deescape-special-chars" should be replaced to <trg> for supported languages
        with open("configs/default.filters.json") as f:
            config_str = f.read()
            config_str = config_str.replace("<src>", src).replace("<trg>", trg)
            abs_path_patterns = os.path.abspath("configs/remove_frequent_patterns.txt")
            config_str = config_str.replace(
                "configs/remove_frequent_patterns.txt", abs_path_patterns
            )
            config = json.loads(config_str)
        print("Using filter default.filters.json")

    with open(output, "w") as f:
        json.dump(config, f, indent=2)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3

"""
Get the statistical distribution of a dataset.
"""

import argparse
import gzip
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import zstandard
from matplotlib import ticker

# Ensure the pipeline is available on the path.
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))

from pipeline.common.downloads import (
    RemoteGzipLineStreamer,
    RemoteZstdLineStreamer,
)
from pipeline.common.logging import get_logger

logger = get_logger(__file__)


def get_line_streamer(file_location: str):
    """Streams in lines from remote locations, or from disk. Accepts zst, gz, and plain text."""
    if file_location.startswith("http://") or file_location.startswith("https://"):
        if file_location.endswith(".zst"):
            return RemoteZstdLineStreamer(file_location)
        # Assume gzip.
        return RemoteGzipLineStreamer(file_location)

    if file_location.endswith(".gz"):
        return gzip.open(file_location, "rt")
    if file_location.endswith(".zst"):
        return zstandard.open(file_location, "rt")
    return open(file_location, "rt")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,  # Preserves whitespace in the help text.
    )
    parser.add_argument(
        "--file_location", type=str, required=True, help="A url or file path for analyzing."
    )
    parser.add_argument(
        "--output_dir", type=str, required=True, help="The directory for the output."
    )
    parser.add_argument("--dataset", type=str, required=True, help="The name of the dataset")
    parser.add_argument(
        "--language",
        type=str,
        required=True,
        help="The dataset language, as a BCP-47 language tag",
    )

    parsed_args = parser.parse_args()

    logger.info(f"file_location: {parsed_args.file_location}")
    logger.info(f"output_dir: {parsed_args.output_dir}")
    logger.info(f"dataset: {parsed_args.dataset}")
    logger.info(f"language: {parsed_args.language}")

    # Compute the distributions for both the codepoints, and word size.
    codepoints_distribution = Histogram()
    word_distribution = Histogram()
    with get_line_streamer(parsed_args.file_location) as lines:
        for line in lines:
            codepoints_distribution.count(len(line))
            word_distribution.count(len(line.split()))

    plot_logarithmic_histogram(
        word_distribution,
        max_size=5_000,  # words
        title="\n".join(
            [
                "Word Count Distribution",
                f"{parsed_args.dataset} - {parsed_args.language}",
            ]
        ),
        x_axis_label="Words (log scale)",
        filename=os.path.join(parsed_args.output_dir, "distribution-words.png"),
    )

    plot_logarithmic_histogram(
        codepoints_distribution,
        max_size=10_000,  # codepoints
        title="\n".join(
            [
                "Codepoints per Sentence Distribution",
                f"{parsed_args.dataset} - {parsed_args.language}",
            ]
        ),
        x_axis_label="Codepoints (log scale)",
        filename=os.path.join(parsed_args.output_dir, "distribution-codepoints.png"),
    )


class Histogram:
    """Computes a histogram based on counts."""

    def __init__(self) -> None:
        # The keys are the bins, the values are the counts.
        self.data: dict[int, int] = {}

    def count(self, count: int):
        if count not in self.data:
            self.data[count] = 0
        self.data[count] += 1

    def log_scale_bins(self, max_size: int, bin_count: int = 30) -> list[int]:
        """Converts the linear bins of the histogram into into logscale bins."""
        # Start with a few small value bins, since it's easy to start with some small fractional
        # values on a log scale.
        bins = [1.0, 2.0]
        for edge in np.logspace(np.log10(1), np.log10(max_size), bin_count):
            if edge > 2.0:
                bins.append(edge)
        return bins


def plot_logarithmic_histogram(
    histogram: Histogram, max_size: int, title: str, x_axis_label: str, filename: str
):
    """
    Converts a histogram of values into a logscale graph, where the x axis is logarithmic,
    and the y scale is linear. The x axis represents the bins of the histogram.
    """

    bins = np.array(histogram.log_scale_bins(max_size))

    # Plot a histogram with logarithmic bins.
    plt.title(title)
    plt.hist(histogram.data.keys(), bins=bins, weights=histogram.data.values(), alpha=0.7)

    plt.xlabel(x_axis_label)
    plt.xscale("log")
    plt.xticks(ticks=bins, labels=[f"{int(edge)}" for edge in bins], rotation="vertical")

    plt.ylabel("Frequency (linear)")
    plt.yscale("linear")
    plt.gca().yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))

    # Ensure no labels are cut off.
    plt.tight_layout()

    logger.info(f"Saving plot to: {filename}")
    plt.savefig(filename, dpi=150)
    plt.close()


if __name__ == "__main__":
    main()

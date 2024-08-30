import argparse
import glob
import json
import os
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Generator

from pipeline.common.datasets import shuffle_with_max_lines
from pipeline.common.downloads import read_lines, write_lines
from pipeline.common.logging import get_logger

logger = get_logger("merge-mono")

# TODO(CJK) - Issue #424
MAX_WORDS_IN_SENTENCE = 100


def hash_line(line: str) -> int:
    """
    Return a hash of a line. The line has its whitespace stripped and text representation
    normalized to ensure a consistent representation.
    """
    cleaned_line = unicodedata.normalize("NFC", line.strip())
    return hash(cleaned_line)


@dataclass
class FilteringStatistics:
    """
    Gather statistics about the filtering process.
    """

    # The size of the merged parallel corpus.
    parallel_corpus_lines: int = 0

    # How much of the monolingual data was duplicated in the merged parallel corpus.
    duplicates_of_parallel_corpus: int = 0

    # How much of the monolingual data was duplicated across the monolingual datasets.
    duplicates_of_monolingual_corpus: int = 0

    # What was the size of the monolingual data that was filtered. This doesn't count the
    # truncation of datasets at the datasets gathering time.
    original_monolingual_lines: int = 0

    # After deduplication, how much monolingual data is left.
    deduplicated_monolingual_lines: int = 0

    # After truncation via the config's `experiment.mono-max-sentences-src.total`,
    # how many lines are left.
    final_truncated_monolingual_lines: int = 0

    # The amount of codepoints in the final monolingual corpus.
    final_truncated_monolingual_codepoints: int = 0

    def save_json(self, path: Path) -> None:
        with open(path, "w", encoding="utf-8") as json_file:
            json.dump(asdict(self), json_file, indent=2)


def filter_and_write_monolingual_data(
    mono_datasets: list[str],
    output_path: Path,
    parallel_hashes: set[int],
    max_lines: int,
    sample_size: int,
    stats: FilteringStatistics,
) -> None:
    """
    Filtering is done with a set[int]. Seeing if a line is in the set should be O(1)
    in terms of time complexity. A set[int] was chosen (storing the hash) rather than
    a set[str], as the latter would retain the string in memory.
    """

    mono_hashes = set()

    def deduplicate_lines(lines: Generator[str, None, None]) -> Generator[str, None, None]:
        """
        This is the generator that will perform the deduplication on a line stream. It's passed
        into the shuffler, so needs to be its own function.
        """
        parallel_discards = 0
        mono_discards = 0
        retained = 0
        for line in lines:
            hashed_line = hash_line(line)
            # Don't add this sentence if it's in the original parallel corpus, or if it's
            # already present in the monolingual data, perhaps from another source.
            if hashed_line in parallel_hashes:
                parallel_discards += 1
            elif hashed_line in mono_hashes:
                mono_discards += 1
            else:
                retained += 1
                mono_hashes.add(hashed_line)  # Don't add this sentence again.

                # Report progress periodically.
                if retained % 1_000_000 == 0:
                    discards = parallel_discards + mono_discards
                    logger.info(f"{retained:,} kept, {discards:,} discarded")

                yield line

        stats.original_monolingual_lines = parallel_discards + mono_discards + retained
        stats.duplicates_of_parallel_corpus = parallel_discards
        stats.duplicates_of_monolingual_corpus = mono_discards
        stats.deduplicated_monolingual_lines = retained
        stats.parallel_corpus_lines = len(parallel_hashes)

    # Estimate the byte size. The better the estimate, the better the data distribution will be.
    # When filtering mono NLLB data against parallel NLLB data, roughly 70% is kept.
    byte_size_estimate = 0
    for dataset in mono_datasets:
        byte_size_estimate += os.path.getsize(dataset)
    byte_size_estimate *= 0.7

    logger.info("Deduplicated and shuffling lines in memory.")
    with read_lines(mono_datasets) as mono_dataset_lines:
        final_lines = shuffle_with_max_lines(
            line_stream=deduplicate_lines(
                mono_dataset_lines,
            ),
            seed=347489345,
            max_lines=max_lines,
            max_words_in_sentence=MAX_WORDS_IN_SENTENCE,
            total_byte_size=byte_size_estimate,
        )

    logger.info(f"Write the final file: {output_path}")
    with write_lines(output_path) as outfile:
        stats.final_truncated_monolingual_lines = len(final_lines)
        for i, line in enumerate(final_lines):
            stats.final_truncated_monolingual_codepoints += len(line)
            outfile.write(line)
            if i % 1_000_000 == 999_999:
                logger.info(f"Wrote line {i+1:,} to {output_path}")

    sample_path = output_path.parent / f"{output_path.stem}.sample.txt"
    logger.info(f"Write a 10,000 line sample of the final: {sample_path}")
    with write_lines(sample_path) as outfile:
        for line in shuffle_with_max_lines(
            line_stream=final_lines,
            seed=9834523434,
            max_lines=sample_size,
            max_words_in_sentence=MAX_WORDS_IN_SENTENCE,
            total_byte_size=os.path.getsize(output_path),
        ):
            outfile.write(line)

    stats_path = output_path.parent / f"{output_path.stem}.stats.json"
    logger.info(f"Save the stats: {stats_path}")
    stats.save_json(stats_path)


def compute_line_hashes(path: Path) -> set[int]:
    """
    In order to de-duplicate sentences we can compute a hash and store it in memory. This makes
    it so that we don't have to store the full sentence in memory. It's about 10 bytes per int
    stored in the set.
    """
    line_hashes: set[int] = set()
    sentences_visited = 0

    with read_lines(path) as lines:
        for line in lines:
            sentences_visited += 1
            if sentences_visited % 1_000_000 == 0:
                logger.info(f"Hashing sentence {sentences_visited:,}")
            line_hashes.add(hash_line(line))

    return line_hashes


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge monolingual datasets.")
    parser.add_argument(
        "--parallel_corpus",
        type=Path,
        help="The path to the parallel corpus of this language, e.g. $MOZ_FETCHES_DIR/corpus.ca.zst",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="The path to the output compressed file, e.g. /builds/worker/artifacts/mono.ca.zst",
    )
    parser.add_argument(
        "--max_sentences", type=int, help="The maximum number of sentences that will be merged."
    )
    parser.add_argument(
        "--datasets_glob",
        type=str,
        help="A glob-style path to the mono datasets, e.g. /path/to/*.zst",
    )
    parser.add_argument(
        "--sample_size", type=int, default=10_000, help="Generate a random sample of sentences."
    )

    args = parser.parse_args()

    output_path: Path = args.output
    max_sentences: int = args.max_sentences
    parallel_corpus: str = args.parallel_corpus
    mono_dataset_paths: list[str] = glob.glob(args.datasets_glob)

    if not mono_dataset_paths:
        raise FileNotFoundError(f"No files found matching glob pattern: {args.datasets_glob}")

    logger.info("Monolingual datasets:")
    for path in mono_dataset_paths:
        logger.info(f" - {path}")

    # Ensure output directory exists
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Compute the line hashes so that the monolingual data can be de-duplicated.
    # It's about 10 bytes per hash in a set, so for a 100 million sentence corpus,
    # it would be ~1G in memory.
    logger.info(f"Compute hashes of the parallel data: {path}")
    line_hashes: set[int] = compute_line_hashes(parallel_corpus)

    stats = FilteringStatistics()

    filter_and_write_monolingual_data(
        mono_dataset_paths, output_path, line_hashes, max_sentences, args.sample_size, stats
    )

    logger.info("Done: Merging monolingual datasets")


if __name__ == "__main__":
    main()

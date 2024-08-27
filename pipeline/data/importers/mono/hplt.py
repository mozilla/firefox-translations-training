import json
import random
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Generator

from pipeline.common.datasets import FilteringStep, Statistics, shuffle_with_max_lines
from pipeline.common.downloads import read_lines, write_lines
from pipeline.common.logging import get_logger
from pipeline.common.memory import log_memory

logger = get_logger(__name__)

random.seed(38947598475)


@dataclass
class HPLTDocument:
    """
    A structured type for the HPLT document entry in a jsonl file.
    https://hplt-project.org/datasets/v1.2

    Usage:
        doc = Document(**json)
    """

    id: int
    document_lang: str
    # The list of scores for each line.
    scores: list[float]
    # The detected language for the sentence.pl
    langs: list[str]
    # All of the text, split by newlines.
    text: str
    # Where this URL was scraped: https://hip.univ-orleans.fr/ipac20/ipac.jsp?session=166R9L62F6723.6585606&profile=scd&menu=search&ts=1660916246772
    url: str
    # e.g. "cc40"
    collection: str

    def __post_init__(self):
        # The sentences in the text, which were separated by newliens.
        self.lines = self.text.split("\n")


@dataclass
class FilteringStatistics(Statistics):
    """
    Gather statistics about the filtering process.
    """

    shards: FilteringStep
    oversampling: FilteringStep
    final: FilteringStep
    document_count: int

    def __init__(self, dataset_path: Path) -> None:
        super().__init__(dataset_path)
        self.shards = FilteringStep(
            dataset_path,
            "How many shards were sampled from. Each shard contains a subset of the "
            "total datasets available",
        )
        self.oversampling = FilteringStep(
            dataset_path,
            "The sentences are oversampled in order to get a more representative sample "
            "of the data.",
        )
        self.final = FilteringStep(
            dataset_path,
            "The final filtering step of datasets. This is what will be used for training.",
        )
        self.document_count = 0


def load_shard_urls(language: str) -> list[str]:
    """
    Download the list of shards, e.g.

    https://data.hplt-project.org/one/monotext/cleaned/en/en_100.jsonl.zst
    https://data.hplt-project.org/one/monotext/cleaned/en/en_101.jsonl.zst
    https://data.hplt-project.org/one/monotext/cleaned/en/en_102.jsonl.zst
    https://data.hplt-project.org/one/monotext/cleaned/en/en_103.jsonl.zst
    https://data.hplt-project.org/one/monotext/cleaned/en/en_104.jsonl.zst
    ...
    https://data.hplt-project.org/one/monotext/cleaned/en/en_110.jsonl.zst
    """

    url = f"https://data.hplt-project.org/one/monotext/cleaned/{language}_map.txt"
    logger.info(f"Downloading shard list: {url}")

    with read_lines(url) as lines:
        shard_urls = []
        for line in lines:
            shard_urls.append(line.strip())
    random.Random(url).shuffle(shard_urls)

    logger.info(f"Available shards for {language}:")
    for lines in shard_urls:
        logger.info(f" - {lines}")
    return shard_urls


class Downloader:
    """
    Controls the logic of over-sampling the HPLT datasets to provide a representative sample.
    The max_lines are loaded fully into memory, shuffled, and then written out to disk.
    """

    def __init__(
        self,
        language: str,
        max_lines: int,
        min_fluency_threshold: float,
        oversample_factor: float,
        stack: ExitStack,
        file_destination: Path,
        max_words_in_sentence: int,
    ) -> None:
        self.visited_lines = 0
        self.language: str = language
        self.max_lines: int = max_lines
        self.min_fluency_threshold = min_fluency_threshold
        self.oversample_line_count = int(max_lines * oversample_factor)
        self.stack = stack
        self.file_destination = file_destination
        self.max_words_in_sentence = max_words_in_sentence
        self.stats = FilteringStatistics(file_destination)

    def estimate_total_byte_size(self, average_bytes_per_line: float):
        """This is required for the distribution of the shuffling behavior."""
        size_estimate = int(average_bytes_per_line * self.oversample_line_count)
        logger.info(f"Size estimate computed: {size_estimate:,} bytes")
        return size_estimate

    def run(self):
        """
        Oversample HPLT, loading up to max_lines in memory, and then shuffle and write it to disk.
        """
        shuffle_stream = shuffle_with_max_lines(
            line_stream=self.oversample_hplt_iterator(),
            seed=f"hplt-{self.language}",
            max_lines=self.max_lines,
            max_words_in_sentence=self.max_words_in_sentence,
            estimate_total_byte_size=self.estimate_total_byte_size,
        )

        logger.info(
            f"Finished loading HPLT data in memory, write it out to {self.file_destination}"
        )

        outfile = self.stack.enter_context(write_lines(self.file_destination))
        for line in shuffle_stream:
            self.stats.final.kept += 1
            outfile.write(line)
            if self.stats.final.kept % 1_000_000 == 0:
                logger.info(
                    f"Wrote {self.stats.final.kept:,} / {self.max_lines:,} lines "
                    f"to: {self.file_destination.name}"
                )
                log_memory()

        self.stats.final.filtered = self.visited_lines - self.stats.final.kept

        logger.info(f"Wrote {self.stats.final.kept:,} lines to: {self.file_destination}")
        stat_path = self.stats.save_json()
        logger.info(f"Saved filtering stats to: {stat_path}")

    def oversample_hplt_iterator(self) -> Generator[str, None, None]:
        """
        Oversample HPLT data, as there is usually more data than we need and we want to make sure
        we have a more representative sample of the data. This way a single document or bias in
        the ordering of the shard is not over-represented in the final data.
        """
        stats = self.stats

        logger.info(f"Oversample the HPLT datasets with {self.oversample_line_count} lines")

        def count_shards_visited():
            stats.shards.filtered -= 1
            stats.shards.kept += 1

        shard_urls = load_shard_urls(self.language)
        stats.shards.filtered = len(shard_urls)
        document_stream = self.stack.enter_context(
            read_lines(shard_urls, on_enter_location=count_shards_visited)
        )

        for document_json in document_stream:
            self.stats.document_count += 1

            document = HPLTDocument(**json.loads(document_json))

            for score, lang_item, sentence in zip(document.scores, document.langs, document.lines):
                self.visited_lines += 1

                if lang_item == self.language and score >= self.min_fluency_threshold:
                    stats.oversampling.kept += 1
                    yield sentence + "\n"
                else:
                    stats.oversampling.filtered += 1

                if self.visited_lines % 1_000_000 == 0:
                    logger.info(f"Visited {self.visited_lines:,} lines")
                    logger.info(
                        f"Kept {stats.oversampling.kept:,} with a target of {self.oversample_line_count:,} for oversampling."
                    )
                    log_memory()

                if stats.oversampling.kept == self.oversample_line_count:
                    return


def download_hplt(
    language: str,
    min_fluency_threshold: float,
    max_lines: int,
    max_words_in_sentence,
    file_destination: Path,
    oversample_factor: float = 2.0,
):
    """
    Downloads and filters the HPLT dataset.
    https://hplt-project.org/datasets/v1.2

    The function oversamples the data to ensure a more representative sample, filters the data
    based on the specified language and minimum score, and writes the final dataset to the
    specified file destination.

    Parameters:
     - language: The BCP 47 language code to filter the documents.
     - min_fluency_threshold: The minimum score a sentence must have to be included in the final dataset.
     - max_lines: The maximum number of lines to include in the final dataset.
     - max_words_in_sentence: The maximum number of words allowed in each sentence.
     - file_destination: The destination path where the final dataset will be written.
     - oversample_factor: The factor by which to oversample the data.
    """

    with ExitStack() as stack:
        downloader = Downloader(
            language=language,
            max_lines=max_lines,
            min_fluency_threshold=min_fluency_threshold,
            oversample_factor=oversample_factor,
            stack=stack,
            file_destination=file_destination,
            max_words_in_sentence=max_words_in_sentence,
        )
        downloader.run()

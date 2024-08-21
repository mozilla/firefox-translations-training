import json
import random
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path

from pipeline.common.datasets import CountingStep, FilteringStep, Statistics
from pipeline.common.downloads import location_exists, read_lines, write_lines
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
    visited_lines: FilteringStep
    document_count: CountingStep
    final_lines: CountingStep

    def __init__(self, dataset_path: Path) -> None:
        super().__init__(dataset_path)
        self.shards = FilteringStep(
            dataset_path,
            "How many shards were sampled from. Each shard contains a subset of the "
            "total datasets available.",
        )
        self.visited_lines = FilteringStep(
            dataset_path,
            "How many lines were visited and kept from the HPLT documents.",
        )
        self.document_count = CountingStep(
            dataset_path,
            "How many documents were visited. This can help represent data diversity.",
        )
        self.final_lines = CountingStep(
            dataset_path,
            "How many lines were actually written. Smaller lines will be combined together.",
        )

    def count_shards_visited(self):
        self.shards.filtered -= 1
        self.shards.kept += 1


def language_has_hplt_support(language: str) -> bool:
    return location_exists(
        f"https://data.hplt-project.org/one/monotext/cleaned/{language}_map.txt"
    )


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


def download_hplt(
    language: str,
    min_fluency_threshold: float,
    max_lines: int,
    max_words_in_sentence,
    file_destination: Path,
):
    """
    Downloads and filters the HPLT dataset.
    https://hplt-project.org/datasets/v1.2

    In the English data with a fluency score of 0.9, about 5% of the total sentences visited
    are fluent enough to keep. That means to generate a monolingual dataset of 100 million
    lines 2 billion lines need to be visited.

    Parameters:
     - language: The BCP 47 language code to filter the documents.
     - min_fluency_threshold: The minimum score a sentence must have to be included in the final dataset.
     - max_lines: The maximum number of lines to include in the final dataset.
     - max_words_in_sentence: The maximum number of words allowed in each sentence.
     - file_destination: The destination path where the final dataset will be written.
    """

    with ExitStack() as stack:
        stats = FilteringStatistics(file_destination)

        outfile = stack.enter_context(write_lines(file_destination))

        shard_urls = load_shard_urls(language)
        stats.shards.filtered = len(shard_urls)
        document_stream = stack.enter_context(
            read_lines(shard_urls, on_enter_location=stats.count_shards_visited)
        )

        visited_lines = 0

        # Subtract 1 as the final newline is written outside of the for loop.
        last_line = max_lines - 1

        for document_json in document_stream:
            stats.document_count.value += 1

            document = HPLTDocument(**json.loads(document_json))

            cumulative_word_count = 0
            has_written_once = False

            # Visit the lines in the document.
            for score, lang_item, line in zip(document.scores, document.langs, document.lines):
                visited_lines += 1

                # Check for the fluency scores.
                if lang_item == language and score >= min_fluency_threshold:
                    # TODO(CJK) - Issue #424
                    word_count = len(line.split())

                    if word_count > max_words_in_sentence:
                        # This sentence is too long.
                        cumulative_word_count = 0
                    else:
                        stats.visited_lines.kept += 1

                        if has_written_once:
                            # Determine if this sentence should be added to the previous one or
                            # written out as a new line. Only concurrent sentences that meet
                            # the fluency requirement will be combined together.
                            if (
                                cumulative_word_count
                                and cumulative_word_count + word_count < max_words_in_sentence
                            ):
                                # Combine sentences together in the outfile.
                                cumulative_word_count += word_count
                                outfile.write(" ")
                            else:
                                cumulative_word_count = 0
                                outfile.write("\n")
                                stats.final_lines.value += 1

                        # Actually write out the line. The next iteration will determine
                        # if it's a complete sentence, or if it should be added onto.
                        outfile.write(line)
                        has_written_once = True
                        stats.visited_lines.kept += 1
                else:
                    cumulative_word_count = 0

                if visited_lines % 5_000_000 == 0:
                    logger.info(f"Visited {visited_lines:,} lines")
                    logger.info(f"Kept {stats.visited_lines.kept:,}.")
                    logger.info(f"Wrote {stats.final_lines.value:,} out of {max_lines:,}.")
                    log_memory()

                if stats.final_lines.value == last_line:
                    break
            if stats.final_lines.value == last_line:
                break

        # Account for the final line.
        outfile.write("\n")
        stats.final_lines.value += 1

        stats.visited_lines.filtered = visited_lines - stats.visited_lines.kept
        logger.info(f"Wrote {stats.final_lines.value:,} lines to: {file_destination}")
        stat_path = stats.save_json()
        logger.info(f"Saved filtering stats to: {stat_path}")

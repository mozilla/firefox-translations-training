import json
import random
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path

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


def download_hplt(
    language: str,
    min_fluency_threshold: float,
    max_sentences: int,
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
     - max_sentences: The maximum number of sentences to include in the final dataset.
     - max_words_in_sentence: The maximum number of words allowed in each sentence.
     - file_destination: The destination path where the final dataset will be written.
     - oversample_factor: The factor by which to oversample the data.
    """
    shard_urls = load_shard_urls(language)
    stats = FilteringStatistics(file_destination)

    oversample_line_count = int(max_sentences * oversample_factor)
    file_destination_tmp = file_destination.parent / f"{file_destination.stem}.tmp.zst"
    visited_lines = 0

    stats.shards.filtered = len(shard_urls)

    def count_shards_visited():
        stats.shards.filtered -= 1
        stats.shards.kept += 1

    logger.info(
        f"Oversample the HPLT datasets and write {oversample_line_count} lines to: {file_destination_tmp}"
    )

    # Oversample HPLT data, as there is usually more data than we need and write it to a tmp
    # file. We oversample to make sure we have a more representative sample of the data. This
    # way a single document or bias in the ordering of the shard is not over-represented in the
    # final data.
    with ExitStack() as stack:
        outfile = stack.enter_context(write_lines(file_destination_tmp))
        document_stream = stack.enter_context(
            read_lines(shard_urls, on_enter_location=count_shards_visited)
        )

        for document_json in document_stream:
            stats.document_count += 1

            document = HPLTDocument(**json.loads(document_json))

            for score, lang_item, sentence in zip(document.scores, document.langs, document.lines):
                visited_lines += 1

                if lang_item == language and score >= min_fluency_threshold:
                    stats.oversampling.kept += 1
                    outfile.write(sentence)
                    outfile.write("\n")
                else:
                    stats.oversampling.filtered += 1

                if visited_lines % 1_000_000 == 0:
                    tmp_file_size = file_destination_tmp.stat().st_size
                    logger.info(f"Visited {visited_lines:,} lines")
                    logger.info(
                        f"Kept {stats.oversampling.kept:,} / {oversample_line_count:,} lines for oversampling."
                    )
                    logger.info(f"{file_destination_tmp.name} size: {tmp_file_size:,} bytes")
                    log_memory()

                # Break out of both loops if we've visited enough lines.
                if stats.oversampling.kept == oversample_line_count:
                    break
            if stats.oversampling.kept == oversample_line_count:
                break

    tmp_file_size = file_destination_tmp.stat().st_size
    logger.info(f"Final oversample {file_destination_tmp.name}: {tmp_file_size:,} bytes")
    log_memory()

    logger.info(f"Write the final data out to: {file_destination}")
    # Load the oversampled dataset up to `max_words_in_sentence` into memory. While it is
    # loaded it is shuffled. Then write it out to the final destination.
    with ExitStack() as stack:
        outfile = stack.enter_context(write_lines(file_destination))
        shuffle_stream = shuffle_with_max_lines(
            line_stream=stack.enter_context(read_lines(file_destination_tmp)),
            seed=f"hplt-{language}",
            max_lines=max_sentences,
            max_words_in_sentence=max_words_in_sentence,
            total_byte_size=tmp_file_size,
        )

        for line in shuffle_stream:
            stats.final.kept += 1
            outfile.write(line)
            if stats.final.kept % 1_000_000 == 0:
                logger.info(
                    f"Wrote {stats.final.kept:,} / {max_sentences:,} lines to: {file_destination.name}"
                )
                log_memory()

        stats.final.filtered = visited_lines - stats.final.kept

    logger.info(f"Wrote {visited_lines} lines to: {file_destination}")
    file_destination_tmp.unlink()
    stat_path = stats.save_json()
    logger.info(f"Saved filtering stats to: {stat_path}")

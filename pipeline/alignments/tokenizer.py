#!/usr/bin/env python3
"""
Tokenizes a text file with line separated sentences using Moses tokenizer.

Example:
  python pipeline/alignments/tokenizer.py --input_path=data/datasets/news.2023.en.shuffled.deduped \
    --output_path=data/datasets/news.2023.en.shuffled.deduped.moses --lang=en --chunk_size=500000

Using C++ opus-fast-mosestokenizer sometimes requires specifying LD_LIBRARY_PATH before starting the Python process
see https://github.com/Helsinki-NLP/opus-fast-mosestokenizer/issues/6
export LD_LIBRARY_PATH=.../<you-python-env>/lib/python3.10/site-packages/mosestokenizer/lib

"""
import argparse
import multiprocessing
from typing import List

from tqdm import tqdm

from pipeline.common.logging import get_logger

logger = get_logger("tokenizer")


def _read_file_in_chunks(file_path, chunk_size):
    with open(file_path, "r", encoding="utf-8") as file:
        while True:
            lines = file.readlines(chunk_size)
            if not lines:
                break
            yield lines


def _tokenize_lines(params) -> List[str]:
    lines, lang = params
    from mosestokenizer import MosesTokenizer

    try:
        # Use aggressive dash splitting to reduce vocabulary size
        tokenizer = MosesTokenizer(lang, aggressive_dash_splits=True)
    except RuntimeError as err:
        msg = str(err)
        if "No known abbreviations for language" in msg:
            # Fall-back to English if the language is not found
            tokenizer = MosesTokenizer("en", aggressive_dash_splits=True)
        else:
            raise err

    tokenized = []
    for line in lines:
        tokens = tokenizer.tokenize(line)
        tokenized.append(" ".join(tokens))
    return tokenized


def tokenize_moses(
    input_path: str, output_path: str, lang: str, sentences_per_chunk: int = 100000
) -> None:
    logger.info(f"Tokenizing {input_path} with Moses tokenizer")

    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
        with open(output_path, "w") as output_file:
            chunks = _read_file_in_chunks(input_path, chunk_size=sentences_per_chunk)

            pbar = tqdm(mininterval=10)
            # ~100K sentences per second on a single core
            for tokenized_chunk in pool.imap(
                _tokenize_lines,
                ((ch, lang) for ch in chunks),
            ):
                output_file.write("\n".join(tokenized_chunk) + "\n")
                pbar.update(len(tokenized_chunk))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__,
        # Preserves whitespace in the help text.
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--output_path",
        metavar="OUTPUT_PATH",
        type=str,
        help="Output file",
    )
    parser.add_argument(
        "--input_path",
        metavar="INPUT_PATH",
        type=str,
        default=None,
        help="Input file",
    )
    parser.add_argument(
        "--lang",
        metavar="LANG",
        type=str,
        default=None,
        help="Language",
    )
    parser.add_argument(
        "--chunk_size",
        metavar="CHUNK_SIZE",
        type=int,
        default=None,
        help="Number of lines to process per chunk",
    )
    args = parser.parse_args()
    tokenize_moses(args.input_path, args.output_path, args.lang, args.chunk_size)

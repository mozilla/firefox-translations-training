#!/usr/bin/env python3
"""
Calculates alignments for a parallel corpus

Example:
    BIN=bin python pipeline/alignments/align.py \
        --corpus_src=fetches/corpus.ru.zst
        --corpus_trg=fetches/corpus.en.zst
        --output_path=artifacts/corpus.aln.zst
        --priors_input_path=fetches/corpus.priors
        --priors_output_path=artifacts/corpus.priors
"""

import argparse
import os
import shutil
import subprocess
import sys
from contextlib import ExitStack
from enum import Enum
from typing import Dict, Optional

import zstandard

from pipeline.common.logging import get_logger

logger = get_logger("alignments")
COMPRESSION_CMD = "zstdmt"


class Tokenization(Enum):
    spaces = "spaces"
    moses = "moses"


def run(
    corpus_src: str,
    corpus_trg: str,
    output_path: str,
    priors_input_path: Optional[str],
    priors_output_path: Optional[str],
    tokenization: Tokenization,
):
    bin = os.environ["BIN"]
    src = os.environ["SRC"]
    trg = os.environ["TRG"]

    tmp_dir = os.path.join(os.path.dirname(output_path), "tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    corpus_src = decompress(corpus_src)
    corpus_trg = decompress(corpus_trg)

    if tokenization == Tokenization.moses:
        tokenized_src, tokenized_trg = corpus_src + ".moses", corpus_trg + ".moses"
        output_aln = os.path.join(tmp_dir, "aln")
        tokenize(corpus_src, tokenized_src, src)
        tokenize(corpus_trg, tokenized_trg, trg)
    else:
        tokenized_src, tokenized_trg = corpus_src, corpus_trg
        output_aln = output_path

    fwd_path, rev_path = align(
        corpus_src=tokenized_src,
        corpus_trg=tokenized_trg,
        priors_input_path=priors_input_path,
        tmp_dir=tmp_dir,
    )
    symmetrize(bin=bin, fwd_path=fwd_path, rev_path=rev_path, output_path=output_aln)

    if priors_output_path:
        write_priors(
            corpus_src=tokenized_src,
            corpus_trg=tokenized_trg,
            fwd_path=fwd_path,
            rev_path=rev_path,
            priors_output_path=priors_output_path,
        )

    if tokenization == Tokenization.moses:
        remapped_aln = os.path.join(tmp_dir, "aln.remapped")
        remap(corpus_src, corpus_trg, tokenized_src, tokenized_trg, output_aln, remapped_aln)
        if output_path.endswith(".zst"):
            logger.info("Compressing final alignments")
            subprocess.check_call([COMPRESSION_CMD, "--rm", remapped_aln])
            remapped_aln += ".zst"
        shutil.move(remapped_aln, output_path)


def decompress(file_path: str):
    if file_path.endswith(".zst"):
        logger.info(f"Decompressing file {file_path}")
        subprocess.check_call([COMPRESSION_CMD, "-d", "-f", "--rm", file_path])
        return file_path[:-4]
    return file_path


def tokenize(input_path: str, output_path: str, lang: str) -> None:
    try:
        from mosestokenizer import MosesTokenizer
    except RuntimeError:
        # https://github.com/Helsinki-NLP/opus-fast-mosestokenizer/issues/6
        import pkgutil

        module_path = pkgutil.find_loader("mosestokenizer").get_filename()
        lib_path = os.path.abspath(os.path.join(os.path.dirname(module_path), "lib"))
        logger.warning(f"Setting LD_LIBRARY_PATH to {lib_path}")
        os.environ["LD_LIBRARY_PATH"] = lib_path
        from mosestokenizer import MosesTokenizer

    from tqdm import tqdm

    logger.info(f"Tokenizing {input_path} with Moses tokenizer")
    tokenizer = MosesTokenizer(lang)

    with open(input_path, "r") as input_file, open(output_path, "w") as output_file:
        for line in tqdm(input_file, mininterval=60):
            tokens = tokenizer.tokenize(line)
            output_file.write(" ".join(tokens) + "\n")


def align(
    corpus_src: str,
    corpus_trg: str,
    priors_input_path: Optional[str],
    tmp_dir: str,
):
    import eflomal

    with ExitStack() as stack:
        if priors_input_path:
            logger.info(f"Using provided priors: {priors_input_path}")
            priors_input = stack.enter_context(open(priors_input_path, "r", encoding="utf-8"))
        else:
            priors_input = None

        # We use eflomal aligner.
        # It is less memory intensive than fast_align.
        # fast_align failed with OOM in a large white-space tokenized corpus
        aligner = eflomal.Aligner()

        src_input = stack.enter_context(open(corpus_src, "r", encoding="utf-8"))
        trg_input = stack.enter_context(open(corpus_trg, "r", encoding="utf-8"))
        fwd_path = os.path.join(tmp_dir, "aln.fwd")
        rev_path = os.path.join(tmp_dir, "aln.rev")
        logger.info("Calculating alignments...")
        aligner.align(
            src_input,
            trg_input,
            links_filename_fwd=fwd_path,
            links_filename_rev=rev_path,
            priors_input=priors_input,
            quiet=False,
            use_gdb=False,
        )
        return fwd_path, rev_path


def symmetrize(bin: str, fwd_path: str, rev_path: str, output_path: str):
    """
    Symmetrize the forward and reverse alignments of the corpus.

    Alignments are generated in two directions, source to target, and target to source.
    This function symmetrizes them so that both directions share the same alignment information.
    It uses `atools` binary from `fast_align`
    """
    logger.info("Symmetrizing alignments...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    # Wrap the file with a compressor stream if it needs to be compressed
    with ExitStack() as stack:
        with zstandard.ZstdCompressor().stream_writer(
            stack.enter_context(open(output_path, "wb"))
        ) if output_path.endswith(".zst") else stack.enter_context(
            open(output_path, "w", encoding="utf-8")
        ) as stream:
            with subprocess.Popen(
                [
                    os.path.join(bin, "atools"),
                    "-i",
                    fwd_path,
                    "-j",
                    rev_path,
                    "-c",
                    "grow-diag-final-and",
                ],
                stdout=subprocess.PIPE,
                text=True,
                bufsize=1,
                encoding="utf-8",
            ) as proc:
                for line in proc.stdout:
                    stream.write(line.encode("utf-8") if output_path.endswith(".zst") else line)

                proc.wait()
                # Check for any errors in the subprocess execution
                if proc.returncode != 0:
                    logger.error(f"atools exit code: {proc.returncode}")
                    raise subprocess.CalledProcessError(proc.returncode, proc.args)


def write_priors(
    corpus_src: str,
    corpus_trg: str,
    fwd_path: str,
    rev_path: str,
    priors_output_path: str,
):
    import eflomal

    logger.info("Calculating priors...")
    with ExitStack() as stack:
        src_input = stack.enter_context(open(corpus_src, "r", encoding="utf-8"))
        trg_input = stack.enter_context(open(corpus_trg, "r", encoding="utf-8"))
        fwd_f = stack.enter_context(open(fwd_path, "r", encoding="utf-8"))
        rev_f = stack.enter_context(open(rev_path, "r", encoding="utf-8"))
        priors_tuple = eflomal.calculate_priors(src_input, trg_input, fwd_f, rev_f)
        logger.info(f"Writing priors to {priors_output_path}...")
        priors_output = stack.enter_context(open(priors_output_path, "w", encoding="utf-8"))
        eflomal.write_priors(priors_output, *priors_tuple)


def map_indices(tok_sentence: str, orig_sentence: str) -> Dict[int, int]:
    """
    Map token indices from tokenized sentence to original sentence.
    :param tok_sentence: tokenized sentence
    :param orig_sentence: original sentence
    :return: Dictionary of indices that maps tokenized words to original words
    """
    tok_words = tok_sentence.split()
    orig_words = orig_sentence.split()
    tok_to_orig_indices = {}
    orig_idx = 0
    tok_idx = 0

    # For 'Hello, world!'
    # Map ['Hello', ',', 'world', '!'] [0, 1, 2, 3]
    # To ['Hello,', 'world!'] [0, 1]
    # tok -> orig: {0: 0, 1: 0, 2: 1, 3: 1}

    while orig_idx < len(orig_words):
        orig_word = orig_words[orig_idx]
        word = ""
        while tok_idx < len(tok_words) and word != orig_word:
            word += tok_words[tok_idx]
            tok_to_orig_indices[tok_idx] = orig_idx
            tok_idx += 1

        orig_idx += 1

    return tok_to_orig_indices


def remap(
    src_path: str,
    trg_path: str,
    tok_src_path: str,
    tok_trg_path: str,
    aln_path: str,
    output_aln_path: str,
):
    """
    Remaps alignments that were calculated for Moses-tokenized corpus to whitespace-tokenized ones.
    :param src_path: path to whitespace-tokenized sentences in source language
    :param trg_path: path to whitespace-tokenized sentences in target language
    :param tok_src_path: path to Moses tokenization sentences in source language
    :param tok_trg_path: path to Moses tokenization sentences in target language
    :param aln_path: path to the alignments calcualate for Moses-tokenized corpus
    :param output_aln_path: path to output alignments file remapped to whitespace-tokenized corpus
    """
    logger.info("Remapping alignments to whitespace tokenization")

    with ExitStack() as stack:
        output = stack.enter_context(open(output_aln_path, "w"))
        for src, trg, tok_src, tok_trg, aln in zip(
            stack.enter_context(open(src_path)),
            stack.enter_context(open(trg_path)),
            stack.enter_context(open(tok_src_path)),
            stack.enter_context(open(tok_trg_path)),
            stack.enter_context(open(aln_path)),
        ):
            # Get the indices mapping
            src_map = map_indices(tok_src, src)
            trg_map = map_indices(tok_trg, trg)

            remapped_aln = []
            for pair in aln.split():
                src_idx, trg_idx = map(int, pair.split("-"))
                new_pair = (src_map[src_idx], trg_map[trg_idx])
                if new_pair not in remapped_aln:
                    remapped_aln.append(new_pair)

            output.write(" ".join([f"{idx1}-{idx2}" for idx1, idx2 in remapped_aln]) + "\n")


def main() -> None:
    logger.info(f"Running with arguments: {sys.argv}")
    parser = argparse.ArgumentParser(
        description=__doc__,
        # Preserves whitespace in the help text.
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument("--type", metavar="TYPE", type=str, help="Dataset type: mono or corpus")
    parser.add_argument(
        "--corpus_src",
        metavar="CORPUS_SRC",
        type=str,
        help="Full path to the source sentences in a parallel dataset. Supports decompression using zstd. "
        "For example `fetches/corpus.ru` or `fetches/corpus.ru.zst`",
    )
    parser.add_argument(
        "--corpus_trg",
        metavar="CORPUS_TRG",
        type=str,
        help="Full path to the target sentences in a parallel dataset. Supports decompression using zstd. "
        "For example `fetches/corpus.en` or `fetches/corpus.en.zst`",
    )
    parser.add_argument(
        "--output_path",
        metavar="OUTPUT_PATH",
        type=str,
        help="A full path to the output alignments file. It will be compressed if the path ends with .zst. "
        "For example artifacts/corpus.aln or artifacts/corpus.aln.zst",
    )
    parser.add_argument(
        "--priors_input_path",
        metavar="PRIORS_INPUT_PATH",
        type=str,
        default=None,
        help="A full path to the model priors calculated in advance. This can speed up generation.",
    )
    parser.add_argument(
        "--priors_output_path",
        metavar="PRIORS_OUTPUT_PATH",
        type=str,
        default=None,
        help="Calculate and save the model priors to the specified file path. "
        "The file will be compressed if it ends with .zst",
    )
    parser.add_argument(
        "--tokenization",
        metavar="TOKENIZATION",
        type=Tokenization,
        choices=list(Tokenization),
        default=Tokenization.spaces,
        help="Use the specified tokenization method. Default is `spaces` which means no tokenization will be applied. "
        "It remaps the alignments back to whitespace tokenized ones if the `moses` tokenization is used.",
    )
    args = parser.parse_args()
    logger.info("Starting generating alignments.")
    run(
        args.corpus_src,
        args.corpus_trg,
        args.output_path,
        args.priors_input_path,
        args.priors_output_path,
        args.tokenization,
    )
    logger.info("Finished generating alignments.")


if __name__ == "__main__":
    main()

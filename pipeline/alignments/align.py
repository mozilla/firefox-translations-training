#!/usr/bin/env python3
"""
Calculates alignments for a parallel corpus

Example:
    python pipeline/alignments/align.py \
        --corpus_prefix=fetches/corpus
        --output_path=artifacts/corpus.aln.zst
        --priors_input_path=fetches/corpus.priors
        --priors_output_path=artifacts/corpus.priors
"""

import argparse
import os
import subprocess
import sys
from contextlib import ExitStack
from typing import Optional

import eflomal
import zstandard

from pipeline.common.logging import get_logger

logger = get_logger("alignments")


def run(
    corpus_prefix: str,
    output_path: str,
    priors_input_path: Optional[str],
    priors_output_path: Optional[str],
):
    src = os.environ["SRC"]
    trg = os.environ["TRG"]
    bin = os.environ["BIN"]
    comp_cmd = os.getenv("COMPRESSION_CMD", "zstd")

    tmp_dir = os.path.join(os.path.dirname(output_path), "tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    logger.info("Decompressing corpus...")
    subprocess.check_call(
        [comp_cmd, "-d", "-f", "--rm", f"{corpus_prefix}.{src}.zst", f"{corpus_prefix}.{trg}.zst"]
    )
    corpus_src = f"{corpus_prefix}.{src}"
    corpus_trg = f"{corpus_prefix}.{trg}"

    with ExitStack() as stack:
        fwd_path, rev_path = align(
            corpus_src=corpus_src,
            corpus_trg=corpus_trg,
            priors_input_path=priors_input_path,
            stack=stack,
            tmp_dir=tmp_dir,
        )
        symmetrize(
            bin=bin, fwd_path=fwd_path, rev_path=rev_path, output_path=output_path, stack=stack
        )

        if priors_output_path:
            write_priors(
                corpus_src=corpus_src,
                corpus_trg=corpus_trg,
                fwd_path=fwd_path,
                rev_path=rev_path,
                priors_output_path=priors_output_path,
                stack=stack,
            )


def align(
    corpus_src: str, corpus_trg: str, priors_input_path: str, stack: ExitStack, tmp_dir: str
):
    if priors_input_path:
        logger.info(f"Using provided priors: {priors_input_path}")
        priors_input = stack.enter_context(open(priors_input_path, "r", encoding="utf-8"))
    else:
        priors_input = None

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


def symmetrize(bin: str, fwd_path: str, rev_path: str, output_path: str, stack: ExitStack):
    logger.info("Symmetrizing alignments...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    # Wrap the file with a compressor stream if it needs to be compressed
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
    stack: ExitStack,
):
    logger.info("Calculating priors...")
    src_input = stack.enter_context(open(corpus_src, "r", encoding="utf-8"))
    trg_input = stack.enter_context(open(corpus_trg, "r", encoding="utf-8"))
    fwd_f = stack.enter_context(open(fwd_path, "r", encoding="utf-8"))
    rev_f = stack.enter_context(open(rev_path, "r", encoding="utf-8"))
    priors_tuple = eflomal.calculate_priors(src_input, trg_input, fwd_f, rev_f)
    logger.info(f"Writing priors to {priors_output_path}...")
    priors_output = stack.enter_context(open(priors_output_path, "w", encoding="utf-8"))
    eflomal.write_priors(priors_output, *priors_tuple)


def main() -> None:
    logger.info(f"Running with arguments: {sys.argv}")
    parser = argparse.ArgumentParser(
        description=__doc__,
        # Preserves whitespace in the help text.
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument("--type", metavar="TYPE", type=str, help="Dataset type: mono or corpus")
    parser.add_argument(
        "--corpus_prefix",
        metavar="CORPUS_PREFIX",
        type=str,
        help="Full path to a parallel dataset without a language and file extension. "
        "For example `fetches/corpus` for files `fetches/corpus.ru.zst` and `fetches/corpus.en.zst`",
    )
    parser.add_argument(
        "--output_path",
        metavar="OUTPUT_PREFIX",
        type=str,
        help="A full path to the output alignments file",
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
    args = parser.parse_args()
    logger.info("Starting generating alignments.")
    run(args.corpus_prefix, args.output_path, args.priors_input_path, args.priors_output_path)
    logger.info("Finished generating alignments.")


if __name__ == "__main__":
    main()

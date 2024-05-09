#!/usr/bin/env python3
"""
Evaluate a trained model with both the BLEU and chrF metrics.

Kinds:
   taskcluster/kinds/evaluate/kind.yml
   taskcluster/kinds/evaluate-quantized/kind.yml
   taskcluster/kinds/evaluate-teacher-ensemble/kind.yml

Example usage:

    $VCS_PATH/pipeline/eval/eval.py
        --src               en                                                 \\
        --trg               ca                                                 \\
        --marian_config     fetches/final.model.npz.best-chrf.npz.decoder.yml  \\
        --models            fetches/final.model.npz.best-chrf.npz              \\
        --dataset_prefix    fetches/wmt09                                      \\
        --artifacts_prefix  artifacts/wmt09                                    \\
        --model_variant     gpu                                                \\
        --workspace         12000                                              \\
        --gpus              4

Artifacts:

For instance for a artifacts_prefix of: "artifacts/wmt09":

  artifacts
  ├── wmt09.en             The source sentences
  ├── wmt09.ca             The target output
  ├── wmt09.ca.ref         The original target sentences
  ├── wmt09.log            The Marian log
  ├── wmt09.metrics        The BLEU and chrF score
  └── wmt09.metrics.json   The BLEU and chrF score in json format

Fetches:

For instance for a value of: "fetches/wmt09":
  fetches
  ├── wmt09.en.zst
  └── wmt09.ca.zst
"""


import argparse
import json
import os
import subprocess
from textwrap import dedent, indent
from typing import Optional

from sacrebleu.metrics.bleu import BLEU, BLEUScore
from sacrebleu.metrics.chrf import CHRF, CHRFScore

from pipeline.common.logging import get_logger

logger = get_logger("eval")


def run_bash_oneliner(command: str):
    """
    Runs multi-line bash with comments as a one-line command.
    """
    command_dedented = dedent(command)

    # Remove comments and whitespace.
    lines = [
        line.strip() for line in command_dedented.split("\n") if line and not line.startswith("#")
    ]
    command = " \\\n".join(lines)

    logger.info("-----------------Running bash in one line--------------")
    logger.info(indent(command_dedented, "  "))
    logger.info("-------------------------------------------------------")
    return subprocess.check_call(command, shell=True)


# De-compresses files, and pipes the result as necessary.
def decompress(path: str, compression_cmd: str, artifact_ext: str):
    subprocess.check_call(f'{compression_cmd} -dc "{path}"')


def main(args_list: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,  # Preserves whitespace in the help text.
    )
    parser.add_argument(
        "--artifacts_prefix",
        type=str,
        help="The location where the translated results will be saved",
    )
    parser.add_argument(
        "--dataset_prefix", type=str, help="The evaluation datasets prefix, used in the form."
    )
    parser.add_argument("--src", type=str, help='The source language, e.g "en".')
    parser.add_argument("--trg", type=str, help='The target language, e.g "ca".')
    parser.add_argument("--marian", type=str, help="The path the to marian binaries.")
    parser.add_argument("--marian_config", type=str, help="The marian yaml config for the model.")
    parser.add_argument(
        "--compression_cmd", default="pigz", help="The name of the compression command to use."
    )
    parser.add_argument(
        "--artifact_ext",
        default="gz",
        help="The artifact extension for the compression",
    )
    parser.add_argument(
        "--quantized",
        action="store_true",
        help="Use a quantized model. This requires the browsermt fork of Marian",
    )
    parser.add_argument(
        "--models",
        type=str,
        help="The Marian model (or models if its an ensemble) to use for translations",
    )
    parser.add_argument(
        "--vocab",
        required=False,
        type=str,
        help="The path to a vocab file (optional)",
    )
    parser.add_argument(
        "--shortlist",
        required=False,
        type=str,
        help="The path to a lexical shortlist (optional)",
    )
    parser.add_argument("--workspace", type=str, help="The preallocated MB for the workspace")
    parser.add_argument(
        "--gpus",
        required=False,
        type=str,
        help="The number of GPUs to use (only for the gpu model variant)",
    )
    parser.add_argument(
        "--model_variant", type=str, help="The model variant to use, (gpu, cpu, quantized)"
    )
    args = parser.parse_args(args_list)

    src = args.src
    trg = args.trg
    dataset_prefix = args.dataset_prefix
    artifacts_prefix = args.artifacts_prefix

    artifacts_dir = os.path.dirname(artifacts_prefix)
    source_file_compressed = f"{dataset_prefix}.{src}.{args.artifact_ext}"
    source_file = f"{artifacts_prefix}.{src}"
    target_file_compressed = f"{dataset_prefix}.{trg}.{args.artifact_ext}"
    target_file = f"{artifacts_prefix}.{trg}"
    target_ref_file = f"{artifacts_prefix}.{trg}.ref"
    marian_decoder = f'"{args.marian}"/marian-decoder'
    marian_log_file = f"{artifacts_prefix}.log"
    language_pair = f"{src}-{trg}"
    metrics_file = f"{artifacts_prefix}.metrics"
    metrics_json = f"{artifacts_prefix}.metrics.json"

    # Configure Marian for the different model variants.
    marian_extra_args = []
    if args.model_variant == "quantized":
        marian_extra_args = ["--int8shiftAlphaAll"]
    elif args.model_variant == "gpu":
        if not args.workspace:
            raise Exception("The workspace size was not provided")
        if not args.gpus:
            raise Exception("The number of GPUs was not provided")
        marian_extra_args = [
            '--workspace', args.workspace,
            '--devices', args.gpus,
        ]  # fmt: skip
    elif not args.model_variant == "cpu":
        raise Exception(f"Unsupported model variant {args.model_variant}")

    if args.vocab:
        # Pass in the vocab twice as it's shared between the source and the target.
        marian_extra_args = [*marian_extra_args, "--vocabs", args.vocab, args.vocab]

    if args.shortlist:
        # The final "false" argument tells Marian not to verify the correctness of the shortlist.
        marian_extra_args = marian_extra_args + ["--shortlist", args.shortlist, "false"]

    logger.info("The eval script is configured with the following:")
    logger.info(f" >          artifacts_dir: {artifacts_dir}")
    logger.info(f" > source_file_compressed: {source_file_compressed}")
    logger.info(f" >            source_file: {source_file}")
    logger.info(f" >            target_file: {target_file}")
    logger.info(f" >        target_ref_file: {target_ref_file}")
    logger.info(f" >         marian_decoder: {marian_decoder}")
    logger.info(f" >        marian_log_file: {marian_log_file}")
    logger.info(f" >          language_pair: {language_pair}")
    logger.info(f" >           metrics_file: {metrics_file}")
    logger.info(f" >           metrics_json: {metrics_json}")
    logger.info(f" >      marian_extra_args: {marian_extra_args}")

    logger.info("Ensure that the artifacts directory exists.")
    os.makedirs(artifacts_dir, exist_ok=True)

    logger.info("Save the original target sentences to the artifacts")

    run_bash_oneliner(
        f"""
        {args.compression_cmd} -dc "{target_file_compressed}" > "{target_ref_file}"
        """
    )

    run_bash_oneliner(
        f"""
        # Decompress the source file, e.g. $fetches/wmt09.en.gz
        {args.compression_cmd} -dc "{source_file_compressed}"

        # Tee the source file into the artifacts directory, e.g. $artifacts/wmt09.en
        | tee "{source_file}"

        # Take the source and pipe it in to be decoded (translated) by Marian.
        | {marian_decoder}
            --models {args.models}
            --config {args.marian_config}
            --quiet
            --quiet-translation
            --log {marian_log_file}
            {" ".join(marian_extra_args)}

        # The translations be "tee"ed out to the artifacts, e.g. $artifacts/wmt09.ca
        | tee "{target_file}"
        """
    )

    with open(target_ref_file, "r") as file:
        target_ref_lines = file.readlines()
    with open(target_file, "r") as file:
        target_lines = file.readlines()

    compute_bleu = BLEU(trg_lang=trg)
    compute_chrf = CHRF()

    logger.info("Computing the BLEU score.")
    bleu_score: BLEUScore = compute_bleu.corpus_score(target_lines, [target_ref_lines])
    bleu_details = json.loads(
        bleu_score.format(signature=compute_bleu.get_signature().format(), is_json=True)
    )

    logger.info("Computing the chrF score.")
    chrf_score: CHRFScore = compute_chrf.corpus_score(target_lines, [target_ref_lines])
    chrf_details = json.loads(
        chrf_score.format(signature=compute_chrf.get_signature().format(), is_json=True)
    )

    data = {
        "bleu": {
            "score": bleu_details["score"],
            # Example details:
            # {
            #     "name": "BLEU",
            #     "score": 0.4,
            #     "signature": "nrefs:1|case:mixed|eff:no|tok:13a|smooth:exp|version:2.0.0",
            #     "verbose_score": "15.6/0.3/0.2/0.1 (BP = 0.823 ratio = 0.837 hyp_len = 180 ref_len = 215)",
            #     "nrefs": "1",
            #     "case": "mixed",
            #     "eff": "no",
            #     "tok": "13a",
            #     "smooth": "exp",
            #     "version": "2.0.0"
            # }
            "details": bleu_details,
        },
        "chrf": {
            "score": chrf_details["score"],
            # Example details:
            # {
            #     "name": "chrF2",
            #     "score": 0.64,
            #     "signature": "nrefs:1|case:mixed|eff:yes|nc:6|nw:0|space:no|version:2.0.0",
            #     "nrefs": "1",
            #     "case": "mixed",
            #     "eff": "yes",
            #     "nc": "6",
            #     "nw": "0",
            #     "space": "no",
            #     "version": "2.0.0"
            # }
            "details": chrf_details,
        },
    }

    logger.info(f"Writing {metrics_json}")
    with open(metrics_json, "w") as file:
        file.write(json.dumps(data, indent=2))

    logger.info(f'Writing the metrics in the older "text" format: {metrics_file}')
    with open(metrics_file, "w") as file:
        file.write(f"{bleu_details['score']}\n{chrf_details['score']}\n")


if __name__ == "__main__":
    main()

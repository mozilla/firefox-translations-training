#!/bin/bash
##
# Evaluate a trained model using a GPU to compute both the BLEU and chrF metrics.
#
# Example usage:
#
#   eval-gpu.sh \
#     $TASK_WORKDIR/artifacts/wmt09                              `# artifacts_prefix` \
#     $MOZ_FETCHES_DIR/wmt09                                     `# dataset_prefix`   \
#     en                                                         `# src`              \
#     ru                                                         `# trg`              \
#     $MOZ_FETCHES_DIR/final.model.npz.best-chrf.npz.decoder.yml `# decoder_config`   \
#     $MOZ_FETCHES_DIR/final.model.npz.best-chrf.npz             `# models`

set -x
set -euo pipefail

echo "###### Evaluation of a model"

if [[ -z "${GPUS:-}" ]]; then
    echo "Error: The GPU environment variable was not provided. This is required as"
    echo "the number of GPUs available for decoding."
    exit 1
fi

if [[ -z "${MARIAN:-}" ]]; then
    echo "Error: The MARIAN environment variable was not provided. This is required as"
    echo "the path to the Marian binary."
    exit 1
fi

if [[ -z "${WORKSPACE:-}" ]]; then
    echo "Error: The WORKSPACE environment variable was not provided. This is required as"
    echo "the amount of MB pre-allocated for decoding."
    exit 1
fi

# The location where the translated results will be saved.
artifacts_prefix=$1
dataset_prefix=$2
src=$3
trg=$4
decoder_config=$5
models=( "${@:6}" )

cd "$(dirname "${0}")"

bash eval.sh \
      "${artifacts_prefix}" \
      "${dataset_prefix}" \
      "${src}" \
      "${trg}" \
      "${MARIAN}" \
      "${decoder_config}" \
      --workspace "${WORKSPACE}" \
      --devices ${GPUS} \
      --models "${models[@]}"

#!/bin/bash
##
# Evaluate a model on GPU.
#

set -x
set -euo pipefail

echo "###### Evaluation of a model"

test -v GPUS
test -v MARIAN
test -v WORKSPACE

res_prefix=$1
dataset_prefix=$2
src=$3
trg=$4
decoder_config=$5
models=( "${@:6}" )

cd "$(dirname "${0}")"

bash eval.sh \
      "${res_prefix}" \
      "${dataset_prefix}" \
      "${src}" \
      "${trg}" \
      "${MARIAN}" \
      "${decoder_config}" \
      -w "${WORKSPACE}" \
      --devices ${GPUS} \
      -m "${models[@]}"
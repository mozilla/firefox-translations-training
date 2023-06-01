#!/bin/bash
##
# Evaluate a quantized model on CPU.
#

set -x
set -euo pipefail

echo "###### Evaluation of a quantized model"

test -v BMT_MARIAN
test -v SRC
test -v TRG

model_path=$1
shortlist=$2
dataset_prefix=$3
vocab=$4
res_prefix=$5
decoder_config=$6

cd "$(dirname "${0}")"

bash eval.sh \
      "${res_prefix}" \
      "${dataset_prefix}" \
      "${SRC}" \
      "${TRG}" \
      "${BMT_MARIAN}" \
      "${decoder_config}" \
      -m "${model_path}" \
      -v "${vocab}" "${vocab}" \
      --shortlist "${shortlist}" false \
      --int8shiftAlphaAll

echo "###### Done: Evaluation of a quantized model"

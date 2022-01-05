#!/bin/bash
##
# Evaluate a model.
#

set -x
set -euo pipefail

echo "###### Evaluation of a model"

res_prefix=$1
dataset_prefix=$2
src=$3
trg=$4
marian=$5
decoder_config=$6
args=( "${@:7}" )

mkdir -p "$(basename "${res_prefix}")"

echo "### Evaluating dataset: ${dataset_prefix}, pair: ${src}-${trg}, Results prefix: ${res_prefix}"

pigz -dc "${dataset_prefix}.${trg}.gz" > "${res_prefix}.${trg}.ref"

pigz -dc "${dataset_prefix}.${src}.gz" |
  tee "${res_prefix}.${src}" |
  "${marian}"/marian-decoder \
    -c "${decoder_config}" \
    --quiet \
    --quiet-translation \
    --log "${res_prefix}.log" \
    "${args[@]}" |
  tee "${res_prefix}.${trg}" |
  sacrebleu "${res_prefix}.${trg}.ref" -d -f text --score-only -l "${src}-${trg}" -m bleu chrf  |
  tee "${res_prefix}.metrics"

echo "###### Done: Evaluation of a model"

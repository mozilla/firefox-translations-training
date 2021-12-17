#!/bin/bash
##
# Evaluate a model.
#

set -x
set -euo pipefail

echo "###### Evaluation of a model"

eval_dir=$1
dataset_prefix=$2
src=$3
trg=$4
marian=$5
decoder_config=$6
args=( "${@:7}" )

mkdir -p "${eval_dir}"
prefix=$(basename "${dataset_prefix}")

echo "### Evaluating dataset: ${prefix}, pair: ${src}-${trg}, Model dir: ${eval_dir}"

pigz -dc "${dataset_prefix}.${trg}.gz" > "${eval_dir}/${prefix}.${trg}.ref"

pigz -dc "${dataset_prefix}.${src}.gz" |
  tee "${eval_dir}/${prefix}.${src}" |
  "${marian}"/marian-decoder \
    -c "${decoder_config}" \
    --quiet \
    --quiet-translation \
    --log "${eval_dir}/${prefix}.log" \
    "${args[@]}" |
  tee "${eval_dir}/${prefix}.${trg}" |
  sacrebleu "${eval_dir}/${prefix}.${trg}.ref" -d -f text --score-only -l "${src}-${trg}" -m bleu chrf  |
  tee "${eval_dir}/${prefix}.metrics"

echo "###### Done: Evaluation of a model"

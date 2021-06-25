#!/bin/bash
##
# Evaluate a quantized model on CPU.
#
# Usage:
#   bash eval.sh model_dir shortlist
#

set -x
set -euo pipefail

echo "###### Evaluation of a quantized model"

test -v MARIAN
test -v TEST_DATASETS
test -v SRC
test -v TRG

model_dir=$1
shortlist=$2

eval_dir="${model_dir}/eval"
vocab="${model_dir}/vocab.spm"

mkdir -p "${eval_dir}"

source "${WORKDIR}/pipeline/setup/activate-python.sh"

echo "### Evaluating a model ${model_dir} on CPU"
for prefix in ${TEST_DATASETS}; do
  echo "### Evaluating ${prefix} ${SRC}-${TRG}"
  sacrebleu -t "${prefix}" -l "${SRC}-${TRG}" --echo src |
    tee "${eval_dir}/${prefix}.${SRC}" |
    "${MARIAN}"/marian-decoder \
      -m "${model_dir}/model.intgemm.alphas.bin" \
      -v "${vocab}" "${vocab}" \
      -c "${WORKDIR}/pipeline/quantize/decoder.yml" \
      --quiet \
      --quiet-translation \
      --log "${eval_dir}/${prefix}.log" \
      --shortlist "${shortlist}" false \
      --int8shiftAlphaAll |
    tee "${eval_dir}/${prefix}.${TRG}" |
    sacrebleu -d -t "${prefix}" -l "${SRC}-${TRG}" |
    tee "${eval_dir}/${prefix}.${TRG}.bleu"

  test -e "${eval_dir}/${prefix}.${TRG}.bleu" || exit 1
done

echo "###### Done: Evaluation of a quantized model"

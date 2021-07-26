#!/bin/bash
##
# Runs quantization of the student model.
#
# Usage:
#   bash quantize.sh model_dir shortlist devtest_src output_dir
#

set -x
set -euo pipefail

echo "###### Quantizing a model"

test -v MARIAN
test -v BIN
test -v SRC
test -v TRG
test -v WORKDIR

model_dir=$1
shortlist=$2
devtest_src=$3
output_dir=$4

res_model="${output_dir}/model.intgemm.alphas.bin"

if [ -e "${res_model}" ]; then
  echo "### Converted model already exists, skipping"
  echo "###### Done: Quantizing a model"
  exit 0
fi

source "${WORKDIR}/pipeline/setup/activate-python.sh"
mkdir -p "${output_dir}"

model="${model_dir}/model.npz.best-bleu-detok.npz"
vocab="${model_dir}/vocab.spm"

cp "${vocab}" "${output_dir}"

echo "### Decoding a sample test set in order to get typical quantization values"
test -s "${output_dir}/quantmults" ||
  "${MARIAN}"/marian-decoder \
    -m "${model}" \
    -v "${vocab}" "${vocab}" \
    -c "${WORKDIR}/pipeline/quantize/decoder.yml" \
    -i "${devtest_src}" \
    -o "${output_dir}/output.${TRG}" \
    --shortlist "${shortlist}" false \
    --quiet \
    --quiet-translation \
    --log "${output_dir}/cpu.output.log" \
    --dump-quantmult \
    2>"${output_dir}/quantmults"

echo "### Quantizing"
test -s "${output_dir}/model.alphas.npz" ||
  "${MARIAN}"/../scripts/alphas/extract_stats.py \
    "${output_dir}/quantmults" \
    "${model}" \
    "${output_dir}/model.alphas.npz"

echo "### Converting"
test -s "${res_model}" ||
  "${MARIAN}"/marian-conv \
    -f "${output_dir}/model.alphas.npz" \
    -t "${res_model}" \
    --gemm-type intgemm8

echo "### The result models is saved to ${res_model}"

echo "###### Done: Quantizing a model"

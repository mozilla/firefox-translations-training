#!/bin/bash
##
# Runs quantization of the student model.
#
# Usage:
#   bash quantize.sh model_dir shortlist devtest_src output_dir
#

set -x
set -euo pipefail

test -v MARIAN
test -v BIN
test -v SRC
test -v TRG
test -v WORKDIR

model_dir=${1}
shortlist=${2}
devtest_src=${3}
output_dir=${4}

mkdir -p "${output_dir}"

model="${model_dir}/model-finetune.npz.best-bleu-detok.npz"
vocab="${model_dir}/vocab.spm"

echo "### Decoding a sample test set in order to get typical quantization values"
test -s "${output_dir}/quantmults" ||
  "${MARIAN}"/marian-decoder \
    -m "${model}" \
    -v "${vocab}" "${vocab}" \
    -c "${WORKDIR}/pipeline/quantize/decoder.yml" \
    -i "${devtest_src}" \
    -o "${output_dir}/output.${TRG}" \
    -w "${WORKSPACE}" \
    -d "${GPUS}" \
    --shortlist "${shortlist}" 50 50 \
    --quiet \
    --quiet-translation \
    --log "${output_dir}/cpu.newstest2013.log" \
    --dump-quantmult \
    2>"${output_dir}/quantmults"

echo "### Quantizing"
test -s "${output_dir}/model.alphas.npz" ||
  "${MARIAN}"/../scripts/alphas/extract_stats.py \
    "${output_dir}/quantmults" \
    "${model}" \
    "${output_dir}/model.alphas.npz"

echo "### Converting"
test -s "${output_dir}/model.intgemm.alphas.bin" ||
  "$MARIAN"/marian-conv \
    -f "${output_dir}/model.alphas.npz" \
    -t "${output_dir}/model.intgemm.alphas.bin" \
    --gemm-type intgemm8

echo "### Evaluation on CPU"
bash "${WORKDIR}"/pipeline/train/eval.sh \
  "${output_dir}" \
  "${SRC}" \
  "${TRG}" \
  "${WORKDIR}/pipeline/quantize/decoder.yml" \
  -v "${vocab}" "${vocab}" \
  -m "${output_dir}/model.intgemm.alphas.bin" \
  --shortlist "${shortlist}" 50 50 \
  --int8shiftAlphaAll

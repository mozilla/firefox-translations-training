#!/bin/bash
##
# Export the quantized model to bergamot translator format.
#
# This script requires the browsermt fork of Marian for the int8shiftAlphaAll mode.
# https://github.com/browsermt/marian-dev
# https://github.com/browsermt/students/tree/master/train-student#5-8-bit-quantization

set -x
set -euo pipefail

echo "###### Exporting a quantized model"

test -v SRC
test -v TRG
test -v BMT_MARIAN

model_dir=$1
shortlist=$2
vocab=$3
output_dir=$4

mkdir -p "${output_dir}"

model="${output_dir}/model.${SRC}${TRG}.intgemm.alphas.bin"
cp "${model_dir}/model.intgemm.alphas.bin" "${model}"
pigz "${model}"

shortlist_bin="${output_dir}/lex.50.50.${SRC}${TRG}.s2t.bin"
"${BMT_MARIAN}"/marian-conv \
  --shortlist "${shortlist}" 50 50 0 \
  --dump "${shortlist_bin}" \
  --vocabs "${vocab}" "${vocab}"
pigz "${shortlist_bin}"

vocab_out="${output_dir}/vocab.${SRC}${TRG}.spm"
cp "${vocab}" "${vocab_out}"
pigz "${vocab_out}"


echo "### Export is completed. Results: ${output_dir}"

echo "###### Done: Exporting a quantized model"

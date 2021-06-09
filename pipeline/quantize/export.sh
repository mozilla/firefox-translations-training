#!/bin/bash
##
# Export the quantized model to bergamot translator format.
#
# Usage:
#   bash export.sh model_dir shortlist output_dir
#

set -x
set -euo pipefail

echo "###### Exporting a quantized model"

test -v SRC
test -v TRG
test -v MARIAN

model_dir=$1
shortlist=$2
output_dir=$3

mkdir -p "${output_dir}"

model="${output_dir}/model.${SRC}${TRG}.intgemm.alphas.bin"
cp "${model_dir}/model.intgemm.alphas.bin" "${model}"
pigz "${model}"

shortlist_bin="${output_dir}/lex.50.50.${SRC}${TRG}.s2t.bin"
"${MARIAN}"/marian-conv \
  --shortlist "${shortlist}" 50 50 0 \
  --dump "${shortlist_bin}" \
  --vocabs "${model_dir}/vocab.spm" "${model_dir}/vocab.spm"
pigz "${shortlist_bin}"

vocab="${output_dir}/vocab.${SRC}${TRG}.spm"
cp "${model_dir}/vocab.spm" "${vocab}"
pigz "${vocab}"

test -s "${output_dir}/model.${SRC}${TRG}.intgemm.alphas.bin.gz" || exit 1
test -s "${output_dir}/lex.50.50.${SRC}${TRG}.s2t.bin.gz" || exit 1
test -s "${output_dir}/vocab.${SRC}${TRG}.spm.gz" || exit 1

echo "### Export is completed. Results: ${output_dir}"

echo "###### Done: Exporting a quantized model"

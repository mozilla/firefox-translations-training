#!/bin/bash
##
# Export the quantized model to bergamot translator format.
#
# Usage:
#   bash export.sh model_dir shortlist output_dir
#

set -x
set -euo pipefail

test -v SRC
test -v TRG

model_dir=${1}
shortlist=${2}
output_dir=${3}

cp "${model_dir}/model.intgemm.alphas.bin" "${output_dir}/model.${SRC}${TRG}.intgemm.alphas.bin"
pigz "${output_dir}/model.${SRC}${TRG}.intgemm.alphas.bin"

cp "${shortlist}" "${output_dir}/lex.50.50.${SRC}${TRG}.s2t.bin.gz"

cp "${model_dir}/vocab.spm" "${output_dir}/vocab.${SRC}${TRG}.spm"
pigz "${output_dir}/vocab.${SRC}${TRG}.spm"


test -s "${output_dir}/model.${SRC}${TRG}.intgemm.alphas.bin.gz" || exit 1
test -s "${output_dir}/lex.50.50.${SRC}${TRG}.s2t.bin.gz" || exit 1
test -s "${output_dir}/vocab.${SRC}${TRG}.spm.gz" || exit 1



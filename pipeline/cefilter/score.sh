#!/bin/bash
##
# Scores a corpus with a reversed NMT model.
#


set -x
set -euo pipefail

echo "###### Scoring"
test -v MARIAN
test -v GPUS
test -v SRC
test -v TRG
test -v WORKSPACE

model=$1
vocab=$2
#note that target will be used as source, since scoring is done with backward model
source_path=$3
target_path=$4
output=$5

# TODO: this should be changed based on replacement of corpus prefix with source and target path
#ARTIFACT_EXT="${ARTIFACT_EXT:-gz}"
#if [ "${ARTIFACT_EXT}" = "zst" ]; then
#  zstdmt --rm -d "${corpus_prefix}.${SRC}.${ARTIFACT_EXT}"
#  zstdmt --rm -d "${corpus_prefix}.${TRG}.${ARTIFACT_EXT}"
#  ARTIFACT_EXT=""
#else
#  ARTIFACT_EXT=".gz"
#fi

dir=$(dirname "${output}")
mkdir -p "${dir}"

"${MARIAN}/marian-scorer" \
  -m "${model}" \
  -v "${vocab}" "${vocab}" \
  -t "${target_path}" "${source_path}" \
  --mini-batch 32 \
  --mini-batch-words 1500 \
  --maxi-batch 1000 \
  --max-length 250 \
  --max-length-crop \
  --normalize \
  -d ${GPUS} \
  -w "${WORKSPACE}" \
  --log "${dir}/scores.txt.log" \
  >"${output}"

echo "###### Done: Scoring"

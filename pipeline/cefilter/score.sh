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
corpus_prefix=$3
output=$4

ARTIFACT_EXT="${ARTIFACT_EXT:-gz}"

if [ "${ARTIFACT_EXT}" = "zst" ]; then
  zstdmt --rm -d "${corpus_prefix}.${SRC}.${ARTIFACT_EXT}"
  zstdmt --rm -d "${corpus_prefix}.${TRG}.${ARTIFACT_EXT}"
  ARTIFACT_EXT=""
else
  ARTIFACT_EXT=".gz"
fi

dir=$(dirname "${output}")
mkdir -p "${dir}"

"${MARIAN}/marian-scorer" \
  --model "${model}" \
  --vocabs "${vocab}" "${vocab}" \
  --train-sets "${corpus_prefix}.${TRG}${ARTIFACT_EXT}" "${corpus_prefix}.${SRC}${ARTIFACT_EXT}" \
  --mini-batch 32 \
  --mini-batch-words 1500 \
  --maxi-batch 1000 \
  --max-length 250 \
  --max-length-crop \
  --normalize \
  --devices ${GPUS} \
  --wworkspace "${WORKSPACE}" \
  --log "${dir}/scores.txt.log" \
  >"${output}"

echo "###### Done: Scoring"

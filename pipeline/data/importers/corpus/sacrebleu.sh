#!/bin/bash
##
# Downloads corpus using sacrebleu
#

set -x
set -euo pipefail

echo "###### Downloading sacrebleu corpus"

src=$1
trg=$2
output_prefix=$3
dataset=$4

COMPRESSION_CMD="${COMPRESSION_CMD:-pigz}"
ARTIFACT_EXT="${ARTIFACT_EXT:-gz}"

{
  set +e

  sacrebleu                         \
    --test-set "${dataset}"         \
    --language-pair "${src}-${trg}" \
    --echo src                      \
  | ${COMPRESSION_CMD} -c > "${output_prefix}.${src}.${ARTIFACT_EXT}"

  sacrebleu                         \
    --test-set "${dataset}"         \
    --language-pair "${src}-${trg}" \
    --echo ref                      \
  | ${COMPRESSION_CMD} -c > "${output_prefix}.${trg}.${ARTIFACT_EXT}"

  status=$?

  set -e
}

if [ $status -ne 0 ]; then
  echo "The first import failed, try again by switching the language pair direction."

  sacrebleu                         \
    --test-set "${dataset}"         \
    --language-pair "${trg}-${src}" \
    --echo src                      \
    | ${COMPRESSION_CMD} -c > "${output_prefix}.${trg}.${ARTIFACT_EXT}"

  sacrebleu                         \
    --test-set "${dataset}"         \
    --language-pair "${trg}-${src}" \
    --echo ref                      \
    | ${COMPRESSION_CMD} -c > "${output_prefix}.${src}.${ARTIFACT_EXT}"
fi


echo "###### Done: Downloading sacrebleu corpus"

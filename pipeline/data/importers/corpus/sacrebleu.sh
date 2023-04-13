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

sacrebleu -t "${dataset}" -l "${src}-${trg}" --echo src | ${COMPRESSION_CMD} -c > "${output_prefix}.${src}.${ARTIFACT_EXT}"
sacrebleu -t "${dataset}" -l "${src}-${trg}" --echo ref | ${COMPRESSION_CMD} -c > "${output_prefix}.${trg}.${ARTIFACT_EXT}"

echo "###### Done: Downloading sacrebleu corpus"

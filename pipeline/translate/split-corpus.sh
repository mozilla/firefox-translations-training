#!/bin/bash
##
# Splits a parallel dataset
#

set -x
set -euo pipefail

corpus_src=$1
corpus_trg=$2
output_dir=$3
num_parts=$4

COMPRESSION_CMD="${COMPRESSION_CMD:-pigz}"
ARTIFACT_EXT="${ARTIFACT_EXT:-gz}"

mkdir -p "${output_dir}"
${COMPRESSION_CMD} -dc "${corpus_src}" |  split -d -n ${num_parts} - "${output_dir}/file."
${COMPRESSION_CMD} -dc "${corpus_trg}" |  split -d -n ${num_parts} - "${output_dir}/file." --additional-suffix .ref

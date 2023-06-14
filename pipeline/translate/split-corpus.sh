#!/bin/bash
##
# Splits a parallel dataset
#

set -x
set -euo pipefail

corpus_src=$1
corpus_trg=$2
output_dir=$3
length=$4

COMPRESSION_CMD="${COMPRESSION_CMD:-pigz}"
ARTIFACT_EXT="${ARTIFACT_EXT:-gz}"

mkdir -p "${output_dir}"
${COMPRESSION_CMD} -dc "${corpus_src}" |  split -d -l ${length} - "${output_dir}/file."
${COMPRESSION_CMD} -dc "${corpus_trg}" |  split -d -l ${length} - "${output_dir}/file." --additional-suffix .ref

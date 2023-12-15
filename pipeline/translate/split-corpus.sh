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

${COMPRESSION_CMD} -dc "${corpus_src}" > decompressed.src
total_lines=$(wc -l < decompressed.src)
lines_per_part=$(( (total_lines + ${num_parts} - 1) / ${num_parts} ))
split -d -l $lines_per_part decompressed.src  "${output_dir}/file."
rm decompressed.src

${COMPRESSION_CMD} -dc "${corpus_trg}" > decompressed.trg
split -d -l $lines_per_part decompressed.trg "${output_dir}/file." --additional-suffix .ref
rm decompressed.trg

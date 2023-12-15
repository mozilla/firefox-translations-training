#!/bin/bash
##
# Splits and deduplicates a monolingual dataset
#


set -x
set -euo pipefail

test -v BIN

mono_path=$1
output_dir=$2
num_parts=$3

COMPRESSION_CMD="${COMPRESSION_CMD:-pigz}"
ARTIFACT_EXT="${ARTIFACT_EXT:-gz}"

mkdir -p "${output_dir}"
${COMPRESSION_CMD} -dc "${mono_path}" | ${BIN}/dedupe > decompressed
total_lines=$(wc -l < decompressed)
lines_per_part=$(( (total_lines + ${num_parts} - 1) / ${num_parts} ))
split -d -l $lines_per_part decompressed "${output_dir}/file."
rm decompressed

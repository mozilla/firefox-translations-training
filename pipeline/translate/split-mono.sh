#!/bin/bash
##
# Splits and deduplicates a monolingual dataset
#


set -x
set -euo pipefail

test -v BIN

mono_path=$1
output_dir=$2
length=$3

COMPRESSION_CMD="${COMPRESSION_CMD:-pigz}"
ARTIFACT_EXT="${ARTIFACT_EXT:-gz}"

mkdir -p "${output_dir}"
${COMPRESSION_CMD} -dc "${mono_path}" | ${BIN}/dedupe | split -d -l ${length} - "${output_dir}/file."

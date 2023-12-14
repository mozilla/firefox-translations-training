#!/bin/bash
#
# Merges translation outputs into a dataset
#

set -x
set -euo pipefail


dir=$1
output_path=$2
mono_path=$3


COMPRESSION_CMD="${COMPRESSION_CMD:-pigz}"

echo "### Collecting translations"
python3 sort_files.py --dir="${dir}" | xargs cat | ${COMPRESSION_CMD} >"${output_path}"

echo "### Comparing number of sentences in source and artificial target files"
src_len=$(${COMPRESSION_CMD} -dc "${mono_path}" | wc -l)
trg_len=$(${COMPRESSION_CMD} -dc "${output_path}" | wc -l)
if [ "${src_len}" != "${trg_len}" ]; then
  echo "### Error: length of ${mono_path} ${src_len} is different from ${output_path} ${trg_len}"
  exit 1
fi

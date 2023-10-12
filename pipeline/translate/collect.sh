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
# To ensure that `file.10.out` comes after `file.9.out` and so on:
# 1. `find "${dir}" -name '*.out'`: This will list all the `.out` files in the directory.
# 2. `sort -t '.' -k2,2n`: This sorts the filenames numerically based on the number after the `.`. The `-t '.'` tells `sort` to use the period as a delimiter, and `-k2,2n` tells it to sort numerically using the second field.
# 3. `xargs cat`: This takes the sorted list of filenames and uses `cat` to concatenate them.
find "${dir}" -name '*.out' | sort -t '.' -k2,2n | xargs cat | ${COMPRESSION_CMD} >"${output_path}"

echo "### Comparing number of sentences in source and artificial target files"
src_len=$(${COMPRESSION_CMD} -dc "${mono_path}" | wc -l)
trg_len=$(${COMPRESSION_CMD} -dc "${output_path}" | wc -l)
if [ "${src_len}" != "${trg_len}" ]; then
  echo "### Error: length of ${mono_path} ${src_len} is different from ${output_path} ${trg_len}"
  exit 1
fi

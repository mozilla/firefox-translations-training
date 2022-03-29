#!/bin/bash
#
# Merges translation outputs into a dataset
#

set -x
set -euo pipefail

test -v TRG

#dir=$1
output_path=$1
mono_path=$2

inputs=( "${@:3}" )

cat "${inputs[@]}" >"${output_path}"

#echo "### Collecting translations"
#pigz -dc "${dir}"/*.gz | pigz >"${output_path}"

echo "### Comparing number of sentences in source and artificial target files"
src_len=$(pigz -dc "${mono_path}" | wc -l)
trg_len=$(pigz -dc "${output_path}" | wc -l)
if [ "${src_len}" != "${trg_len}" ]; then
  echo "### Error: length of ${mono_path} ${src_len} is different from ${output_path} ${trg_len}"
  exit 1
fi

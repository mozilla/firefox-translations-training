#!/bin/bash
##
# Cleans corpus using bicleaner-ai or bicleaner
#

set -x
set -euo pipefail

echo "###### Bicleaner filtering"

test -v SRC
test -v TRG

corpus_prefix=$1
output_prefix=$2
bicleaner_threshold=$3
type=$4
threads=$5

output_dir=$(dirname "${output_prefix}")
tmp_dir="${output_dir}/tmp"
mkdir -p "${tmp_dir}"

if [ "${type}" == 'bicleaner-ai' ]; then
  echo "### Using bicleaner-ai"
  bash "pipeline/bicleaner/download-pack.sh" "${tmp_dir}" "bicleaner-ai"
  cmd=bicleaner-ai-classify
elif [ "${type}" == 'bicleaner' ]; then
  echo "### Using bicleaner"
  bash "pipeline/bicleaner/download-pack.sh" "${tmp_dir}" "bicleaner"
  cmd=bicleaner-classify
else
  echo "### Unsupported type: ${type}"
  exit 1
fi

echo "### Classifying and filtering"
test -s "${tmp_dir}/best.gz" ||
  paste <(pigz -dc "${corpus_prefix}.${SRC}.gz") <(pigz -dc "${corpus_prefix}.${TRG}.gz") |
  ${cmd} --scol 1 --tcol 1 --processes "${threads}"  - - "${tmp_dir}"/*.yaml |
  awk -v threshold=${bicleaner_threshold} '{if ($3>threshold) {print $0}}' |
  pigz >"${tmp_dir}/best.gz"

echo "### Writing output corpus"
pigz -dc "${tmp_dir}/best.gz" | cut -f1 | pigz >"${output_prefix}.${SRC}.gz"
pigz -dc "${tmp_dir}/best.gz" | cut -f2 | pigz >"${output_prefix}.${TRG}.gz"

echo "### Cleaning files"
rm -rf "${tmp_dir}"

echo "###### Done: Bicleaner filtering"

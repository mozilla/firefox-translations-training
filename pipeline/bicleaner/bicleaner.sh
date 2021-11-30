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
pack_dir=$6

output_dir=$(dirname "${output_prefix}")
mkdir -p "${output_dir}"

if [ "${type}" == 'bicleaner-ai' ]; then
  echo "### Using bicleaner-ai"
  cmd=bicleaner-ai-classify
elif [ "${type}" == 'bicleaner' ]; then
  echo "### Using bicleaner"
  cmd=bicleaner-classify
else
  echo "### Unsupported type: ${type}"
  exit 1
fi

echo "### Classifying and filtering"
test -s "${output_prefix}.best.gz" ||
  paste <(pigz -dc "${corpus_prefix}.${SRC}.gz") <(pigz -dc "${corpus_prefix}.${TRG}.gz") |
  ${cmd} --scol 1 --tcol 1 --processes "${threads}"  - - "${pack_dir}"/*.yaml |
  awk -v threshold=${bicleaner_threshold} '{if ($3>threshold) {print $0}}' |
  pigz >"${output_prefix}.best.gz"

echo "### Writing output corpus"
pigz -dc "${output_prefix}.best.gz" |
  tee >(cut -f1 | pigz >"${output_prefix}.${SRC}.gz") |
  cut -f2 | pigz >"${output_prefix}.${TRG}.gz"

echo "### Cleaning files"
rm "${output_prefix}.best.gz"

echo "###### Done: Bicleaner filtering"

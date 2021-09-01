#!/bin/bash
##
# Cleans corpus using bicleaner-ai or bicleaner
#
# Usage:
#   bash bicleaner.sh corpus_prefix output_prefix
#

set -x
set -euo pipefail

echo "###### Bicleaner filtering"

test -v SRC
test -v TRG
test -v CLEAN_TOOLS

corpus_prefix=$1
output_prefix=$2
bicleaner_threshold=$3

output_dir=$(dirname "${output_prefix}")
tmp_dir="${output_dir}/tmp"
mkdir -p "${tmp_dir}"


# bicleaner and bicleaner-ai have conflicting dependencies. installing on demand
if [ ! -e "${output_prefix}.${SRC}.gz" ]; then
  if bash "${CLEAN_TOOLS}/download-bicleaner-pack.sh" "${tmp_dir}" "bicleaner-ai"; then
    echo "### Using bicleaner-ai"
    pip install bicleaner-ai==1.0.1
    cmd=bicleaner-ai-classify
  elif bash "${CLEAN_TOOLS}/download-bicleaner-pack.sh" "${tmp_dir}" "bicleaner"; then
    echo "### Using bicleaner"
    pip install bicleaner==0.14
    cmd=bicleaner-classify
  else
    echo "### Bicleaner language pack is not supported, skipping."
    cp "${corpus_prefix}.${SRC}.gz" "${output_prefix}.${SRC}.gz"
    cp "${corpus_prefix}.${TRG}.gz" "${output_prefix}.${TRG}.gz"
    exit 0
  fi
fi

echo "### Classifying and filtering"
test -s "${output_prefix}.${SRC}.gz" || test -s "${tmp_dir}/best.gz" ||
  paste <(pigz -dc "${corpus_prefix}.${SRC}.gz") <(pigz -dc "${corpus_prefix}.${TRG}.gz") |
  ${cmd} --scol 1 --tcol 1 - - "${tmp_dir}"/*.yaml |
  awk -v threshold=${bicleaner_threshold} '{if ($3>threshold) {print $0}}' |
  pigz >"${tmp_dir}/best.gz"

echo "### Writing output corpus"
test -s "${output_prefix}.${SRC}.gz" || pigz -dc "${tmp_dir}/best.gz" | cut -f1 | pigz >"${output_prefix}.${SRC}.gz"
test -s "${output_prefix}.${TRG}.gz" || pigz -dc "${tmp_dir}/best.gz" | cut -f2 | pigz >"${output_prefix}.${TRG}.gz"

echo "### Cleaning files"
rm -rf "${tmp_dir}"

echo "###### Done: Bicleaner filtering"

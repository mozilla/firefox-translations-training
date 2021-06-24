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

PATH="/root/miniconda3/bin:${PATH}"
source /root/miniconda3/etc/profile.d/conda.sh
conda activate bergamot-training-env

threshold=0.7
output_dir=$(dirname "${output_prefix}")
tmp_dir="${output_dir}/tmp"
mkdir -p "${tmp_dir}"


if [ ! -e "${output_prefix}.${SRC}.gz" ]; then
  if bash "${CLEAN_TOOLS}/download-bicleaner-pack.sh" "${tmp_dir}" "bicleaner-ai"; then
    echo "### Using bicleaner-ai"
    cmd=bicleaner-ai-classify
  elif bash "${CLEAN_TOOLS}/download-bicleaner-pack.sh" "${tmp_dir}" "bicleaner"; then
    echo "### Using bicleaner"
    cmd=bicleaner-classify
  else
    echo "### Bicleaner language pack is not supported, skipping"
    exit 0
  fi
fi

echo "### Classifying and filtering"
test -s "${output_prefix}.${SRC}.gz" || test -s "${tmp_dir}/best.gz" ||
  paste <(pigz -dc "${corpus_prefix}.${SRC}.gz") <(pigz -dc "${corpus_prefix}.${TRG}.gz") |
  ${cmd} --scol 1 --tcol 1 - - "${tmp_dir}"/*.yaml |
  awk -v threshold=${threshold} '{if ($3>threshold) {print $0}}' | pigz >"${tmp_dir}/best.gz"

echo "### Writing output corpus"
test -s "${output_prefix}.${SRC}.gz" || pigz -dc "${tmp_dir}/best.gz" | cut -f1 | pigz >"${output_prefix}.${SRC}.gz"
test -s "${output_prefix}.${TRG}.gz" || pigz -dc "${tmp_dir}/best.gz" | cut -f2 | pigz >"${output_prefix}.${TRG}.gz"

echo "### Cleaning files"
rm -rf "${tmp_dir}"

echo "###### Done: Bicleaner filtering"

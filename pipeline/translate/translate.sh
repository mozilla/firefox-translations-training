#!/bin/bash
##
# Translates files
#

set -x
set -euo pipefail

test -v GPUS
test -v MARIAN
test -v WORKSPACE

files=$1
models=$2
vocab=$3
output_dir=$4

for name in ${files}; do
  prefix="${output_dir}/${name}"
  echo "### ${prefix}"
  test -e "${prefix}.nbest" ||
    "${MARIAN}/marian-decoder" \
      -c pipeline/translate/decoder.yml \
      -m ${models} \
      -v "${vocab}" "${vocab}" \
      -i "${prefix}" \
      -o "${prefix}.out" \
      --log "${prefix}.log" \
      -d ${GPUS} \
      -w "${WORKSPACE}"
done

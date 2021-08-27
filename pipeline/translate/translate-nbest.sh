#!/bin/bash
##
# Translates files generating n-best lists as output
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
  "${MARIAN}/marian-decoder" \
    -c pipeline/translate/decoder.yml \
    -m ${models} \
    -v "${vocab}" "${vocab}" \
    -i "${prefix}" \
    -o "${prefix}.nbest" \
    --log "${prefix}.log" \
    --n-best \
    -d ${GPUS} \
    -w "${WORKSPACE}"
done

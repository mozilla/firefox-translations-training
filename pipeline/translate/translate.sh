#!/bin/bash
##
# Translates input dataset
#

set -x
set -euo pipefail

test -v GPUS
test -v MARIAN
test -v WORKSPACE

input=$1
vocab=$2
models=( "${@:3}" )
output="${input}.out"

cd "$(dirname "${0}")"

"${MARIAN}/marian-decoder" \
  --config decoder.yml \
  --models "${models[@]}" \
  --vocabs "${vocab}" "${vocab}" \
  --input "${input}" \
  --output "${output}" \
  --log "${input}.log" \
  --devices ${GPUS} \
  --workspace "${WORKSPACE}"

# Test that the input and output have the same number of sentences.
test "$(wc -l <"${input}")" == "$(wc -l <"${output}")"

#!/bin/bash
##
# Translates files generating n-best lists as output
#

set -x
set -euo pipefail

test -v GPUS
test -v MARIAN
test -v WORKSPACE

input=$1
vocab=$2
models=( "${@:3}" )

output="${input}.nbest"

cd "$(dirname "${0}")"

"${MARIAN}/marian-decoder" \
  --config decoder.yml \
  --models "${models[@]}" \
  --vocabs "${vocab}" "${vocab}" \
  --input "${input}" \
  --output "${output}" \
  --log "${input}.log" \
  --n-best \
  --devices ${GPUS} \
  --workspace "${WORKSPACE}"

# Test that the input and output have the same number of sentences.
test "$(wc -l <"${output}")" -eq "$(( $(wc -l <"${input}") * 8 ))"

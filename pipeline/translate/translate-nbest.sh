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

#randomize mini batch size a bit to get benchmark data
#mini_batch_size=$((2**$(shuf -i 4-9 -n 1)))

cd "$(dirname "${0}")"

"${MARIAN}/marian-decoder" \
  -c decoder.yml \
  -m "${models[@]}" \
  -v "${vocab}" "${vocab}" \
  -i "${input}" \
  -o "${input}.nbest" \
  --log "${input}.log" \
  --n-best \
  -d ${GPUS} \
  -w "${WORKSPACE}"
  #--mini-batch "${mini_batch_size}"

test "$(wc -l <"${input}.nbest")" -eq "$(( $(wc -l <"${input}") * 8 ))"

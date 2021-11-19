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


cd "$(dirname "${0}")"

"${MARIAN}/marian-decoder" \
  -c decoder.yml \
  -m "${models[@]}" \
  -v "${vocab}" "${vocab}" \
  -i "${input}" \
  -o "${input}.out" \
  --log "${input}.log" \
  -d ${GPUS} \
  -w "${WORKSPACE}"

test "$(wc -l <"${input}")" == "$(wc -l <"${input}.out")"

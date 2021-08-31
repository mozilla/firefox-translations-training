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


"${MARIAN}/marian-decoder" \
  -c pipeline/translate/decoder.yml \
  -m ${@:3} \
  -v "${vocab}" "${vocab}" \
  -i "${input}" \
  -o "${input}.out" \
  --log "${input}.log" \
  -d ${GPUS} \
  -w "${WORKSPACE}"


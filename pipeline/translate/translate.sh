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

models=( "${@:3}" )
modeldir=$(dirname ${models})

#if the model is an OPUS-MT model, use the model vocab instead of the defined forward vocab
opusvocab=$(ls ${modeldir}/opus*.vocab.yml)
if [ -n ${opusvocab} ]; then
    vocab=${opusvocab}
else
    vocab=$2
fi

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

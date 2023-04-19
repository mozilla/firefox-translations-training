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
models=( "${@:3}" )
modeldir=$(dirname ${models})
#if the model is an OPUS-MT model, use the model vocab instead of the defined forward vocab
opusvocab=$(ls ${modeldir}/opus*.vocab.yml)
if [ -n ${opusvocab} ]; then
    vocab=${opusvocab}
else
    vocab=$2
fi

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

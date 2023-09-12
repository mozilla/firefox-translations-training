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
output=$2
models=( "${@:4}" )
modeldir=$(dirname ${models})


#if the model is an OPUS-MT model, use the model vocab instead of the defined forward vocab
for opus_vocab in ${modeldir}/opus*.vocab.yml; do
    if [[ -f ${opus_vocab} ]]; then
	vocab=${opus_vocab}
	else
	vocab=$3
    fi
    break
done

cd "$(dirname "${0}")"

"${MARIAN}/marian-decoder" \
  -c decoder.yml \
  -m "${models[@]}" \
  -v "${vocab}" "${vocab}" \
  -i "${input}" \
  -o "${output}" \
  --log "${input}.log" \
  --n-best \
  -d ${GPUS} \
  -w "${WORKSPACE}"

test "$(wc -l <"${output}")" -eq "$(( $(wc -l <"${input}") * 8 ))"

#!/bin/bash
##
# Train SentencePiece vocabulary model
#
# Usage:
#   bash spm-vocab.sh <corpus_src> <corpus_trg> <vocab_output>
#

set -x
set -euo pipefail

test -v MARIAN

corpus_src=$1
corpus_trg=$2
vocab_output=$3

vocab_dir=$(dirname "${vocab_output}")
mkdir -p "${vocab_dir}"

pigz -dc "${corpus_src}" | shuf -n 10000000 >"${vocab_dir}/data.txt"
pigz -dc "${corpus_trg}" | shuf -n 10000000 >>"${vocab_dir}/data.txt"

"${MARIAN}/spm_train" --bos_id=-1 --eos_id=0 --unk_id=1 --user_defined_symbols="" \
  --input="${vocab_dir}/data.txt" --model_prefix="${vocab_dir}/vocab" --vocab_size=32000

mv "${vocab_dir}/vocab.model" "${vocab_output}"

#!/bin/bash
##
# Train SentencePiece vocabulary model
#

set -x
set -euo pipefail

test -v MARIAN

corpus_src=$1
corpus_trg=$2
vocab_output=$3
sample_size=$4

vocab_dir=$(dirname "${vocab_output}")
mkdir -p "${vocab_dir}"

cat <(pigz -dc "${corpus_src}") <(pigz -dc "${corpus_trg}") |
"${MARIAN}/spm_train" --bos_id=-1 --eos_id=0 --unk_id=1 --user_defined_symbols="" \
  --model_prefix="${vocab_dir}/vocab" --vocab_size=32000 \
  --input_sentence_size="${sample_size}" --shuffle_input_sentence=true

mv "${vocab_dir}/vocab.model" "${vocab_output}"

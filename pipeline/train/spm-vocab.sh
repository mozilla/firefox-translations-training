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
threads=$5

if [ "$threads" = "auto" ]; then
  threads=$(nproc)
fi

COMPRESSION_CMD="${COMPRESSION_CMD:-pigz}"

vocab_dir=$(dirname "${vocab_output}")
mkdir -p "${vocab_dir}"

${COMPRESSION_CMD} -dc "${corpus_src}" >"${vocab_dir}/data.src.txt"
${COMPRESSION_CMD} -dc "${corpus_trg}" >"${vocab_dir}/data.trg.txt"

"${MARIAN}/spm_train" --bos_id=-1 --eos_id=0 --unk_id=1 --user_defined_symbols="" \
  --model_prefix="${vocab_dir}/vocab" --vocab_size=32000 \
  --input="${vocab_dir}/data.src.txt,${vocab_dir}/data.trg.txt" \
  --input_sentence_size="${sample_size}" --shuffle_input_sentence=true \
  --num_threads "${threads}"

rm "${vocab_dir}/data.src.txt" "${vocab_dir}/data.trg.txt"

mv "${vocab_dir}/vocab.model" "${vocab_output}"

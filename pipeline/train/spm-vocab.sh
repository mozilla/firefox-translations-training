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
vocab_size="${6:-32000}"

if (( vocab_size % 8 != 0 )); then
  echo "Error: vocab_size must be a multiple of 8 (https://github.com/mozilla/firefox-translations-training/issues/249)"
  exit 1
fi

if [ "$threads" = "auto" ]; then
  threads=$(nproc)
fi

COMPRESSION_CMD="${COMPRESSION_CMD:-pigz}"

vocab_dir=$(dirname "${vocab_output}")
mkdir -p "${vocab_dir}"

${COMPRESSION_CMD} -dc "${corpus_src}" >"${vocab_dir}/data.src.txt"
${COMPRESSION_CMD} -dc "${corpus_trg}" >"${vocab_dir}/data.trg.txt"

# https://github.com/hplt-project/OpusTrainer/tree/main#generating-vocabulary-and-tags-before-training
# byte_fallback - decomposes unknown pieces into UTF-8 bytes
# user_defined_symbols - placeholders
# character_coverage - CJK is recommended to have 0.9995, vocab languages probably you want 1
"${MARIAN}/spm_train" --bos_id=-1 --eos_id=0 --unk_id=1 \
  --user_defined_symbols="__source__,__target__,__done__,__start__,__end__" \
  --model_prefix="${vocab_dir}/vocab" --vocab_size="${vocab_size}" \
  --input="${vocab_dir}/data.src.txt,${vocab_dir}/data.trg.txt" \
  --input_sentence_size="${sample_size}" --shuffle_input_sentence=true \
  --byte_fallback \
  --character_coverage=1.0 \
  --num_threads "${threads}"

rm "${vocab_dir}/data.src.txt" "${vocab_dir}/data.trg.txt"

mv "${vocab_dir}/vocab.model" "${vocab_output}"

#!/bin/bash
##
# Train the SentencePiece vocabulary model. This outputs a ".spm" binary file, and the
# ".vocab" file which is a human readable list of the vocabulary. The vocab file is
# what is used to tokenize text input for the machine learning model. The vocab that
# is generated is a mix of the source and target languages.
#
# Kinds:
#   taskcluster/ci/train-vocab/kind.yml
#
# Example usage:
#
#   export MARIAN=$MOZ_FETCHES_DIR            && \
#   spm-vocab.sh                                 \
#       fetches/corpus.en.zst  `# corpus_src`    \
#       fetches/corpus.ca.zst  `# corpus_trg`    \
#       artifacts/vocab.spm    `# vocab_output`  \
#       10000000               `# sample_size`   \
#       auto                   `# threads`       \
#       32000                  `# vocab_size`

set -x
set -euo pipefail

test -v MARIAN

# The name of the source corpus, e.g. "fetches/corpus.en.zst".
corpus_src=$1
# The name of the target corpus, e.g. "fetches/corpus.ca.zst".
corpus_trg=$2
# Where the vocab file will be output, e.g. "artifacts/vocab.spm"
vocab_output=$3
# The maximum number of sentences to train on, e.g. 10000000
sample_size=$4
# The thread count, either "auto" or an int.
threads=$5
# The size of the final vocab. Defaults to 32000.
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

# The input arguments are available here:
#   https://github.com/google/sentencepiece/blob/master/doc/options.md
#
# https://github.com/hplt-project/OpusTrainer/tree/main#generating-vocabulary-and-tags-before-training
# byte_fallback - decomposes unknown pieces into UTF-8 bytes
# user_defined_symbols - placeholders
# character_coverage - CJK is recommended to have 0.9995, vocab languages probably you want 1
"${MARIAN}/spm_train" \
  --bos_id=-1 \
  --eos_id=0 \
  --unk_id=1 \
  --user_defined_symbols="__source__,__target__,__done__,__start__,__end__" \
  --model_prefix="${vocab_dir}/vocab" \
  --vocab_size="${vocab_size}" \
  --input="${vocab_dir}/data.src.txt,${vocab_dir}/data.trg.txt" \
  --input_sentence_size="${sample_size}" \
  --shuffle_input_sentence=true \
  --byte_fallback \
  --character_coverage=1.0 \
  --num_threads "${threads}"

rm "${vocab_dir}/data.src.txt" "${vocab_dir}/data.trg.txt"

mv "${vocab_dir}/vocab.model" "${vocab_output}"

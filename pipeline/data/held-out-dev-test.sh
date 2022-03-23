#!/bin/bash
##
# Separate held-out dev and test sets from corpus
#

set -x
set -euo pipefail

test -v SRC
test -v TRG


corpus_src=$1
corpus_trg=$2
dev_size=$3
test_size=$4
output_path_prefix=$5
dataset=$6

tmp="${output_path_prefix}/pasted"
mkdir -p "${tmp}"

# paste and shuffle

paste <(pigz -dc "${corpus_src}") <(pigz -dc "${corpus_trg}") | shuf | pigz > "${tmp}/corpus.shuf.both.gz"

# separate dev and test
pigz -dc "${tmp}/corpus.shuf.both.gz" | sed -n "1,${test_size}p" | pigz > "${tmp}/corpus.test.both.gz"
pigz -dc "${tmp}/corpus.shuf.both.gz" | sed -n "$((${test_size}+1)),$((${test_size}+${dev_size}))p" | pigz > "${tmp}/corpus.dev.both.gz"
pigz -dc "${tmp}/corpus.shuf.both.gz" | tail +"$((${test_size}+${dev_size}+1))" | pigz > "${tmp}/corpus.train.both.gz"

for set in dev test
do
  pigz -dc "${tmp}/corpus.${set}.both.gz" | cut -f1 | pigz > "${output_path_prefix}/${set}/${dataset}.${SRC}.gz"
  pigz -dc "${tmp}/corpus.${set}.both.gz" | cut -f2 | pigz > "${output_path_prefix}/${set}/${dataset}.${TRG}.gz"
done

pigz -dc "${tmp}/corpus.train.both.gz" | cut -f1 | pigz > "${output_path_prefix}/train/${dataset}.${SRC}.gz"
pigz -dc "${tmp}/corpus.train.both.gz" | cut -f2 | pigz > "${output_path_prefix}/train/${dataset}.${TRG}.gz"

echo "###### Done: Creating held-out dev and test sets for ${corpus_src}, ${corpus_trg}"

echo "### Comparing number of sentences in full and train/dev/test files"
src_len=$(pigz -dc "${corpus_src}" | wc -l)
trg_len=$(pigz -dc "${corpus_trg}" | wc -l)

src_test_len=$(pigz -dc "${output_path_prefix}/test/${dataset}.${SRC}.gz" | wc -l)
src_dev_len=$(pigz -dc "${output_path_prefix}/dev/${dataset}.${SRC}.gz" | wc -l)
src_train_len=$(pigz -dc "${output_path_prefix}/train/${dataset}.${SRC}.gz" | wc -l)

trg_test_len=$(pigz -dc "${output_path_prefix}/test/${dataset}.${TRG}.gz" | wc -l)
trg_dev_len=$(pigz -dc "${output_path_prefix}/dev/${dataset}.${TRG}.gz" | wc -l)
trg_train_len=$(pigz -dc "${output_path_prefix}/train/${dataset}.${TRG}.gz" | wc -l)

rm -rf "${tmp}"

if [ "${src_len}" != $((${src_test_len}+${src_dev_len}+${src_train_len})) ]; then
  echo "### Error: length of ${corpus_src} ${src_len} is different from sum of set lengths (${src_test_len}+${src_dev_len}+${src_train_len})"
  exit 1
fi

if [ "${trg_len}" != $((${src_test_len}+${src_dev_len}+${src_train_len})) ]; then
  echo "### Error: length of ${corpus_trg} ${trg_len} is different from sum of set lengths (${trg_test_len}+${trg_dev_len}+${trg_train_len})"
  exit 1
fi

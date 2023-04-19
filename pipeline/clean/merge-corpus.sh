#!/bin/bash
##
# Merges and deduplicates parallel datasets
#

set -x
set -euo pipefail

echo "###### Merging parallel datasets"

test -v SRC
test -v TRG
test -v BIN

output_prefix=$1
max_sents=$2
input_prefixes=( "${@:3}" )

tmp="${output_prefix}/merge"
mkdir -p "${tmp}"

echo "### Merging"
cat "${input_prefixes[@]/%/.${SRC}.gz}" >"${tmp}/corpus.${SRC}.dup.gz"
cat "${input_prefixes[@]/%/.${TRG}.gz}" >"${tmp}/corpus.${TRG}.dup.gz"

echo "### Deduplication"
paste <(pigz -dc "${tmp}/corpus.${SRC}.dup.gz") <(pigz -dc "${tmp}/corpus.${TRG}.dup.gz") |
${BIN}/dedupe |
pigz >"${tmp}.${SRC}${TRG}.gz"

# if max sents not -1, get the first n sents (this is mainly used for testing to make translation and training go faster)
if [ "${max_sents}" != "inf" ]; then
    head -${max_sents} <(pigz -dc "${tmp}.${SRC}${TRG}.gz") | pigz > "${tmp}.${SRC}${TRG}.truncated.gz"
    mv "${tmp}.${SRC}${TRG}.truncated.gz" "${tmp}.${SRC}${TRG}.gz"
fi

pigz -dc "${tmp}.${SRC}${TRG}.gz" | cut -f1 | pigz > "${output_prefix}.${SRC}.gz"
pigz -dc "${tmp}.${SRC}${TRG}.gz" | cut -f2 | pigz > "${output_prefix}.${TRG}.gz"

rm -rf "${tmp}"

echo "###### Done: Merging parallel datasets"

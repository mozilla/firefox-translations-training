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
max_sentences=$2
inputs=( "${@:3}" )

shuf_params=()
if [[ "$max_sentences" != "None" ]]; then
    shuf_params+=(--head-count "$max_sentences")
fi

output_dir=$(dirname "$output_prefix")
tmp="${output_dir}/tmp"
deduplicated_corpus="${tmp}/deduplicated.${SRC}${TRG}.zst"
merged_src="${tmp}/corpus.${SRC}.dup.zst"
merged_trg="${tmp}/corpus.${TRG}.dup.zst"
final_src="${output_prefix}.${SRC}.zst"
final_trg="${output_prefix}.${TRG}.zst"

mkdir -p "${tmp}"

echo "### Merging"
cat `echo ${inputs[@]} | tr ' ' '\n' | grep "${SRC}.zst" | tr '\n' ' '` > "$merged_src"
cat `echo ${inputs[@]} | tr ' ' '\n' | grep "${TRG}.zst" | tr '\n' ' '` > "$merged_trg"

# See pipeline/translate/merge-corpus.sh for more information on the deduplication step.

echo "### Deduplication"

get_seeded_random() {
  set +x
  for i in {1..1000}; do
    echo "merge-corpus-${SRC}-${TRG}-${i}"
  done
  set -x
}

paste <(zstdmt -dc "$merged_src") <(zstdmt -dc "$merged_trg")      |
  ${BIN}/dedupe                                                    |
  shuf --random-source=<(get_seeded_random) "${shuf_params[@]}" |
  zstdmt >"$deduplicated_corpus"

rm "$merged_src" "$merged_trg"

echo "### Splitting languages into separate files"

zstdmt -dc "$deduplicated_corpus" | cut -f1 | zstdmt > "$final_src"
zstdmt -dc "$deduplicated_corpus" | cut -f2 | zstdmt > "$final_trg"

rm -rf "$tmp"

echo "###### Done: Merging parallel datasets"

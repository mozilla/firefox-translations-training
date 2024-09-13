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

tmp="${output_prefix}/merge-tmp"
mkdir -p "${tmp}"

echo "### Merging"
if [[ "${inputs[0]}" == *.zst ]]; then
  cat `echo ${inputs[@]} | tr ' ' '\n' | grep "${SRC}.zst" | tr '\n' ' '` >"${tmp}/corpus.${SRC}.dup.zst"
  cat `echo ${inputs[@]} | tr ' ' '\n' | grep "${TRG}.zst" | tr '\n' ' '` >"${tmp}/corpus.${TRG}.dup.zst"
else
  cat "${inputs[@]/%/.${SRC}.zst}" >"${tmp}/corpus.${SRC}.dup.zst"
  cat "${inputs[@]/%/.${TRG}.zst}" >"${tmp}/corpus.${TRG}.dup.zst"
fi

# See pipeline/translate/merge-corpus.sh for more information on the deduplication step.

echo "### Deduplication"
paste <(zstdmt -dc "${tmp}/corpus.${SRC}.dup.zst") <(zstdmt -dc "${tmp}/corpus.${TRG}.dup.zst") |
${BIN}/dedupe |
zstdmt >"${tmp}.${SRC}${TRG}.zst"

if [[ -n "$max_sentences" ]]; then
  # head generates a 141 SIGPIPE error, which is why || true is needed here.
  zstdmt -dc "${tmp}.${SRC}${TRG}.zst" | head -n "$max_sentences" || true | cut -f1 | zstdmt > "${output_prefix}.${SRC}.zst"
  zstdmt -dc "${tmp}.${SRC}${TRG}.zst" | head -n "$max_sentences" || true | cut -f2 | zstdmt > "${output_prefix}.${TRG}.zst"

else
  zstdmt -dc "${tmp}.${SRC}${TRG}.zst" | cut -f1 | zstdmt > "${output_prefix}.${SRC}.zst"
  zstdmt -dc "${tmp}.${SRC}${TRG}.zst" | cut -f2 | zstdmt > "${output_prefix}.${TRG}.zst"
fi

rm -rf "${tmp}"

echo "###### Done: Merging parallel datasets"

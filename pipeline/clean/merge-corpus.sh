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
inputs=( "${@:2}" )

tmp="${output_prefix}/merge"
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

zstdmt -dc "${tmp}.${SRC}${TRG}.zst" | cut -f1 | zstdmt > "${output_prefix}.${SRC}.zst"
zstdmt -dc "${tmp}.${SRC}${TRG}.zst" | cut -f2 | zstdmt > "${output_prefix}.${TRG}.zst"

rm -rf "${tmp}"

echo "###### Done: Merging parallel datasets"

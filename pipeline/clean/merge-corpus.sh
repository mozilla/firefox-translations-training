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

COMPRESSION_CMD="${COMPRESSION_CMD:-pigz}"
ARTIFACT_EXT="${ARTIFACT_EXT:-gz}"

tmp="${output_prefix}/merge"
mkdir -p "${tmp}"

echo "### Merging"
if [[ "${inputs[0]}" == *.${ARTIFACT_EXT} ]]; then
  cat `echo ${inputs[@]} | tr ' ' '\n' | grep "${SRC}.${ARTIFACT_EXT}" | tr '\n' ' '` >"${tmp}/corpus.${SRC}.dup.${ARTIFACT_EXT}"
  cat `echo ${inputs[@]} | tr ' ' '\n' | grep "${TRG}.${ARTIFACT_EXT}" | tr '\n' ' '` >"${tmp}/corpus.${TRG}.dup.${ARTIFACT_EXT}"
else
  cat "${inputs[@]/%/.${SRC}.${ARTIFACT_EXT}}" >"${tmp}/corpus.${SRC}.dup.${ARTIFACT_EXT}"
  cat "${inputs[@]/%/.${TRG}.${ARTIFACT_EXT}}" >"${tmp}/corpus.${TRG}.dup.${ARTIFACT_EXT}"
fi

echo "### Deduplication"
paste <(${COMPRESSION_CMD} -dc "${tmp}/corpus.${SRC}.dup.${ARTIFACT_EXT}") <(${COMPRESSION_CMD} -dc "${tmp}/corpus.${TRG}.dup.${ARTIFACT_EXT}") |
${BIN}/dedupe |
${COMPRESSION_CMD} >"${tmp}.${SRC}${TRG}.${ARTIFACT_EXT}"

${COMPRESSION_CMD} -dc "${tmp}.${SRC}${TRG}.${ARTIFACT_EXT}" | cut -f1 | ${COMPRESSION_CMD} > "${output_prefix}.${SRC}.${ARTIFACT_EXT}"
${COMPRESSION_CMD} -dc "${tmp}.${SRC}${TRG}.${ARTIFACT_EXT}" | cut -f2 | ${COMPRESSION_CMD} > "${output_prefix}.${TRG}.${ARTIFACT_EXT}"

rm -rf "${tmp}"

echo "###### Done: Merging parallel datasets"

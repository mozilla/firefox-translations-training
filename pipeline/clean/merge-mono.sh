#!/bin/bash
##
# Merges monolingual datasets
#

set -x
set -euo pipefail
test -v BIN

echo "###### Merging monolingual datasets"

output=$1
max_sent=$2
datasets=( "${@:3}" )

LOCALE="${LOCALE:-}"
COMPRESSION_CMD="${COMPRESSION_CMD:-pigz}"
ARTIFACT_EXT="${ARTIFACT_EXT:-gz}"

if [ -z "${LOCALE}" ]; then
  dir=$(dirname "${output}")
  mkdir -p "${dir}"
  ${COMPRESSION_CMD} -dc "${datasets[@]}" |
    ${BIN}/dedupe |
    shuf -n "${max_sent}" |
    ${COMPRESSION_CMD} >"${output}"
else
  datasets=($( printf '%s\n' "${datasets[@]}"| grep ${LOCALE} ))
  output="${output}/mono.${LOCALE}.${ARTIFACT_EXT}"
  ${COMPRESSION_CMD} -dc "${datasets[@]}" |
    ${BIN}/dedupe |
    shuf -n "${max_sent}" |
    ${COMPRESSION_CMD} >"${output}"
fi

echo "###### Done: Merging monolingual datasets"

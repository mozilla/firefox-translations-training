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

COMPRESSION_CMD="${COMPRESSION_CMD:-pigz}"

dir=$(dirname "${output}")
mkdir -p "${dir}"

${COMPRESSION_CMD} -dc "${datasets[@]}" |
  ${BIN}/dedupe |
  shuf -n "${max_sent}" |
  ${COMPRESSION_CMD} >"${output}"


echo "###### Done: Merging monolingual datasets"

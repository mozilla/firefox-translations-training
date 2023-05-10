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

dir=$(dirname "${output}")
mkdir -p "${dir}"

pigz -dc "${datasets[@]}" |
  ${BIN}/dedupe |
  shuf -n "${max_sent}" |
  pigz >"${output}"


echo "###### Done: Merging monolingual datasets"

#!/bin/bash
##
# Downloads evaluation datasets
#
# Usage:
#   bash download-eval.sh dir [datasets...]
#

set -x
set -euo pipefail

echo "###### Downloading evaluation datasets"

test -v SRC
test -v TRG

dir=$1
cache=$2

for dataset in "${@:3}"; do
  name="${dataset//[^A-Za-z0-9_- ]/_}"
  bash "pipeline/data/download-corpus.sh" "${dir}/${name}" "${cache}" "${dataset}" eval

  test -e "${dir}/${name}.${SRC}" || pigz -dk "${dir}/${name}.${SRC}.gz"
  test -e "${dir}/${name}.${TRG}" || pigz -dk "${dir}/${name}.${TRG}.gz"
done


echo "###### Done: Downloading evaluation datasets"

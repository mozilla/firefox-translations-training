#!/bin/bash
##
# Merges datasets into a corpus.
#
# Usage:
#   bash merge-corpus.sh src1 src2 trg1 trg2 res_src res_trg
#

set -x
set -euo pipefail

echo "###### Merging datasets into a corpus"

src1=$1
src2=$2
trg1=$3
trg2=$4
res_src=$5
res_trg=$6

mkdir -p "$(dirname "${res_src}")"
mkdir -p "$(dirname "${res_trg}")"
test -s "${res_src}" || cat <(pigz -dc "${src1}") <(pigz -dc "${src2}") | pigz >"${res_src}"
test -s "${res_trg}" || cat <(pigz -dc "${trg1}") <(pigz -dc "${trg2}") | pigz >"${res_trg}"

src_len=$(pigz -dc "${res_src}" | wc -l)
trg_len=$(pigz -dc "${res_trg}" | wc -l)
if [ "${src_len}" != "${trg_len}" ]; then
  echo "Error: length of ${res_src} ${src_len} is different from ${res_trg} ${trg_len}"
  exit 1
fi

echo "###### Done: Merging datasets into a corpus"

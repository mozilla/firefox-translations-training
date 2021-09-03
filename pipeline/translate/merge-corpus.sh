#!/bin/bash
##
# Merges datasets with shuffling.
#
# Usage:
#   bash merge-corpus.sh src1 src2 trg1 trg2 res_src res_trg
#

set -x
set -euo pipefail

echo "###### Merging datasets"

src1=$1
src2=$2
trg1=$3
trg2=$4
res_src=$5
res_trg=$6

tmp_dir="$(dirname "${res_src}")/tmp"
mkdir -p "${tmp_dir}"

cat <(pigz -dc "${src1}") <(pigz -dc "${src2}") | pigz >"${tmp_dir}/original.src.gz"
cat <(pigz -dc "${trg1}") <(pigz -dc "${trg2}") | pigz >"${tmp_dir}/original.trg.gz"

echo "#### Shuffling"
paste <(pigz -dc "${tmp_dir}/original.src.gz") <(pigz -dc "${tmp_dir}/original.trg.gz") |
  shuf |
  pigz > "${tmp_dir}/all.gz"

pigz -dc "${tmp_dir}/all.gz" | cut -f1 | pigz > "${res_src}"
pigz -dc "${tmp_dir}/all.gz" | cut -f2 | pigz > "${res_trg}"

src_len=$(pigz -dc "${res_src}" | wc -l)
trg_len=$(pigz -dc "${res_trg}" | wc -l)
if [ "${src_len}" != "${trg_len}" ]; then
  echo "Error: length of ${res_src} ${src_len} is different from ${res_trg} ${trg_len}"
  exit 1
fi

rm -rf "${tmp_dir}"

echo "###### Done: Merging datasets"

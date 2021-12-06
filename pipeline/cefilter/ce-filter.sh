#!/bin/bash
##
# Filters student parallel corpus with scores produced by a reversed NMT model.
#

set -x
set -euo pipefail

echo "###### Cross entropy filtering"
test -v SRC
test -v TRG

corpus_prefix=$1
output_prefix=$2
scores=$3

cd "$(dirname "${0}")"

# Part of the data to be removed (0.05 is 5%)
remove=0.05
output_dir=$(dirname "${output_prefix}")
tmp="${output_dir}/tmp"
mkdir -p "${tmp}"

echo "### Sorting scores"
if [ ! -s "${tmp}/sorted.gz" ]; then
  buffer_size="$(echo "$(grep MemTotal /proc/meminfo | awk '{print $2}')"*0.9 | bc | cut -f1 -d.)"
  paste "${scores}" <(pigz -dc "${corpus_prefix}.${SRC}.gz") <(pigz -dc "${corpus_prefix}.${TRG}.gz") |
  LC_ALL=C sort -n -k1,1 -S "${buffer_size}K" -T "${tmp}" |
  pigz >"${tmp}/sorted.gz"
fi

echo "### Cutting the best scored corpus"
if [ ! -s "${tmp}/best.gz" ]; then
  lines=$(pigz -dc "${tmp}/sorted.gz" | wc -l)
  startline=$(echo ${lines}*${remove} | bc | cut -f1 -d.)
  pigz -dc "${tmp}/sorted.gz" | tail -n +${startline} | cut -f2,3 | pigz >"${tmp}/best.gz"
fi

echo "### Writing output corpus"
pigz -dc "${tmp}/best.gz" |
  tee >(cut -f1 | pigz >"${output_prefix}.${SRC}.gz") |
  cut -f2 | pigz >"${output_prefix}.${TRG}.gz"

echo "### Deleting tmp dir"
rm -rf "${tmp}"

echo "###### Done: Cross entropy filtering"

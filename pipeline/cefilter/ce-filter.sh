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

COMPRESSION_CMD="${COMPRESSION_CMD:-pigz}"
ARTIFACT_EXT="${ARTIFACT_EXT:-gz}"

cd "$(dirname "${0}")"

# Part of the data to be removed (0.05 is 5%)
remove=0.05
output_dir=$(dirname "${output_prefix}")
tmp="${output_dir}/tmp"
mkdir -p "${tmp}"

echo "### Sorting scores"
if [ ! -s "${tmp}/sorted.${ARTIFACT_EXT}" ]; then
  buffer_size="$(echo "$(grep MemTotal /proc/meminfo | awk '{print $2}')"*0.9 | bc | cut -f1 -d.)"
  paste "${scores}" <(${COMPRESSION_CMD} -dc "${corpus_prefix}.${SRC}.${ARTIFACT_EXT}") <(${COMPRESSION_CMD} -dc "${corpus_prefix}.${TRG}.${ARTIFACT_EXT}") |
  LC_ALL=C sort -n -k1,1 -S "${buffer_size}K" -T "${tmp}" |
  ${COMPRESSION_CMD} >"${tmp}/sorted.${ARTIFACT_EXT}"
fi

echo "### Cutting the best scored corpus"
if [ ! -s "${tmp}/best.${ARTIFACT_EXT}" ]; then
  lines=$(${COMPRESSION_CMD} -dc "${tmp}/sorted.${ARTIFACT_EXT}" | wc -l)
  startline=$(echo ${lines}*${remove} | bc | cut -f1 -d.)
  ${COMPRESSION_CMD} -dc "${tmp}/sorted.${ARTIFACT_EXT}" | tail -n +${startline} | cut -f2,3 | ${COMPRESSION_CMD} >"${tmp}/best.${ARTIFACT_EXT}"
fi

echo "### Writing output corpus"
${COMPRESSION_CMD} -dc "${tmp}/best.${ARTIFACT_EXT}" |
  tee >(cut -f1 | ${COMPRESSION_CMD} >"${output_prefix}.${SRC}.${ARTIFACT_EXT}") |
  cut -f2 | ${COMPRESSION_CMD} >"${output_prefix}.${TRG}.${ARTIFACT_EXT}"

echo "### Deleting tmp dir"
rm -rf "${tmp}"

echo "###### Done: Cross entropy filtering"

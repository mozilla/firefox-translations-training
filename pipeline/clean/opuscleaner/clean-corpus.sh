#!/bin/bash
##
# Cleaning parallel corpora with OpusCleaner
#

set -x
set -euo pipefail

echo "###### Cleaning corpus with OpusCleaner"

#test -v SRC
#test -v TRG

input_prefix=$1
output_prefix=$2
threads=$3
dataset=$4

COMPRESSION_CMD="${COMPRESSION_CMD:-pigz}"
ARTIFACT_EXT="${ARTIFACT_EXT:-gz}"

if [ "${ARTIFACT_EXT}" != "gz" ]; then
  echo "Error: OpusCleaner supports only Gzip"
  exit 1
fi;

if [ "$threads" = "auto" ]; then
  threads=$(nproc)
fi

cd "$(dirname "${0}")"
dir="$(dirname "${output_prefix}")"
mkdir -p "${dir}"

echo "### Generating cleaning config: ${dataset}.${SRC}-${TRG}.filters.json"
# save new filter to dataset output dir
filter_path="${output_prefix}.${SRC}-${TRG}.filters.json"
python3 generate_filters.py "${input_prefix}" "${SRC}" "${TRG}" "${dataset}" "${filter_path}"
test -s "${filter_path}" || exit 1

echo "### Cleaning ${input_prefix} with filter ${filter_path}"
#can we use stdin to feed input to opuscleaner? this didn't work
#paste <(${COMPRESSION_CMD} -dc "${input_prefix}.${SRC}.${ARTIFACT_EXT}") \
#      <(${COMPRESSION_CMD} -dc "${input_prefix}.${TRG}.${ARTIFACT_EXT}") |
#  opuscleaner-clean \
#    --parallel ${threads} \
#    --batch-size=50000 \
#    --input=- \
#    "${filter_path}" "${SRC}" "${TRG}" |
opuscleaner-clean \
  --parallel ${threads} \
  --batch-size=50000 \
  "${filter_path}" |
  tee >(cut -f1 | ${COMPRESSION_CMD} >"${output_prefix}.${SRC}.${ARTIFACT_EXT}") |
        cut -f2 | ${COMPRESSION_CMD} >"${output_prefix}.${TRG}.${ARTIFACT_EXT}"

test -s "${output_prefix}.${SRC}.${ARTIFACT_EXT}" || exit 1
test -s "${output_prefix}.${TRG}.${ARTIFACT_EXT}" || exit 1

echo "### Clean ${input_prefix} is written to  ${output_prefix}"

echo "###### Done: Cleaning corpus with OpusCleaner"

#!/bin/bash
##
# Cleaning parallel corpora with OpusCleaner
#

set -x
set -euo pipefail

echo "###### Cleaning corpus with OpusCleaner"

test -v SRC
test -v TRG

input_prefix=$1
output_prefix=$2
threads=$3
dataset=$4

COMPRESSION_CMD="${COMPRESSION_CMD:-pigz}"
ARTIFACT_EXT="${ARTIFACT_EXT:-gz}"

if [ "$threads" = "auto" ]; then
  threads=$(nproc)
fi

cd "$(dirname "${0}")"
dir="$(dirname "${output_prefix}")"
mkdir -p "${dir}"


echo "Downloading FastText model"
# pre download fast text model as it's causing constant issues
filters_dir="/builds/worker/.local/lib/python3.10/site-packages/opuscleaner/filters"
wget -O "${filters_dir}/large.bin" https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin

echo "### Generating cleaning config: ${dataset}.${SRC}-${TRG}.filters.json"
# save new filter to dataset output dir
filter_path="${output_prefix}.${SRC}-${TRG}.filters.json"
python3 generate_filters.py "${input_prefix}" "${SRC}" "${TRG}" "${dataset}" "${filter_path}"
test -s "${filter_path}" || exit 1

echo "### Cleaning ${input_prefix} with filter ${filter_path}"
paste <(${COMPRESSION_CMD} -dc "${input_prefix}.${SRC}.${ARTIFACT_EXT}") \
      <(${COMPRESSION_CMD} -dc "${input_prefix}.${TRG}.${ARTIFACT_EXT}") |
opuscleaner-clean \
  --parallel ${threads} \
  --batch-size=50000 \
  --input=- \
  "${filter_path}" "${SRC}" "${TRG}" |
  tee >(cut -f1 | ${COMPRESSION_CMD} >"${output_prefix}.${SRC}.${ARTIFACT_EXT}") |
        cut -f2 | ${COMPRESSION_CMD} >"${output_prefix}.${TRG}.${ARTIFACT_EXT}"

echo "### Checking length of the files"
test -s "${output_prefix}.${SRC}.${ARTIFACT_EXT}" || exit 1
test -s "${output_prefix}.${TRG}.${ARTIFACT_EXT}" || exit 1
new_len_src="$(${COMPRESSION_CMD} -dc "${output_prefix}.${SRC}.${ARTIFACT_EXT}" | wc -l)"
new_len_trg="$(${COMPRESSION_CMD} -dc "${output_prefix}.${TRG}.${ARTIFACT_EXT}" | wc -l)"
orig_len_src="$(${COMPRESSION_CMD} -dc "${input_prefix}.${SRC}.${ARTIFACT_EXT}" | wc -l)"
[[ ${new_len_src} -ge 1 ]] || exit 1
[[ ${new_len_trg} -ge 1 ]] || exit 1
[[ "${new_len_src}" = "${new_len_trg}" ]] || exit 1
echo "### Filtered length: ${new_len_src} / ${orig_len_src}"

echo "### Clean ${input_prefix} is written to  ${output_prefix}"

echo "###### Done: Cleaning corpus with OpusCleaner"

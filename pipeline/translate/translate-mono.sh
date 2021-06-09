#!/bin/bash

# Usage: ./translate-mono.sh mono_path model_dir output_path

set -x
set -euo pipefail

echo "###### Translating monolingual data"

test -v GPUS
test -v MARIAN
test -v WORKSPACE

mono_path=$1
model_dir=$2
output_path=$3

config="${model_dir}/model.npz.best-ce-mean-words.npz.decoder.yml"
decoder_config="${WORKDIR}/pipeline/translate/decoder.yml"
tmp_dir=$(dirname "${output_path}")/tmp

mkdir -p "${tmp_dir}"

echo "### Splitting the corpus into smaller chunks"
test -s "${tmp_dir}/file.00" || pigz -dc "${mono_path}" | split -d -l 500000 - "${tmp_dir}/file."

echo "### Translate source sentences with Marian"
# This can be parallelized across several GPU machines.
for name in $(ls "${tmp_dir}" | grep -E "^file\.[0-9]+$" | shuf); do
  prefix="${tmp_dir}/${name}"
  echo "### ${prefix}"
  test -e "${prefix}.out" ||
    "${MARIAN}/marian-decoder" \
      -c "${config}" "${decoder_config}" \
      -i "${prefix}" \
      -o "${prefix}.out" \
      --log "${prefix}.log" \
      -d "${GPUS}" \
      -w "${WORKSPACE}"
done

echo "### Collecting translations"
cat "${tmp_dir}"/file.*.out | pigz >"${output_path}"

echo "### Comparing number of sentences in source and artificial target files"
src_len=$(pigz -dc "${mono_path}" | wc -l)
trg_len=$(pigz -dc "${output_path}" | wc -l)
if [ "${src_len}" != "${trg_len}" ]; then
  echo "### Error: length of ${mono_path} ${src_len} is different from ${output_path} ${trg_len}"
  exit 1
fi

rm -rf "${tmp_dir}"

echo "###### Done: Translating monolingual data"

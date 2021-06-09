#!/bin/bash
#
# Translates monolingual dataset
#
# Usage: ./translate-corpus.sh corpus_src corpus_trg model_dir output_path

set -x
set -euo pipefail

test -v GPUS
test -v MARIAN
test -v WORKSPACE
test -v WORKDIR

corpus_src=${1}
corpus_trg=${2}
model_dir=${3}
output_path=${4}

config="${model_dir}/model.npz.best-ce-mean-words.npz.decoder.yml"
decoder_config="${WORKDIR}/pipeline/translate/decoder.yml"
tmp_dir=$(dirname "${output_path}")/tmp
mkdir -p "${tmp_dir}"

# Split parallel corpus into smaller chunks.
test -s "${tmp_dir}/file.00" ||
  pigz -dc "${corpus_src}" |
  split -d -l 500000 - "${tmp_dir}/file."
test -s "${tmp_dir}/file.00.ref" ||
  pigz -dc "${corpus_trg}" |
  split -d -l 500000 - "${tmp_dir}/file." --additional-suffix .ref

# Translate source sentences with Marian.
# This can be parallelized across several GPU machines.
for prefix in $(ls "${tmp_dir}" | grep -E "^file\.[0-9]+$" | shuf); do
  echo "### ${prefix}"
  test -e "${prefix}.nbest" ||
    "${MARIAN}/marian-decoder" \
      -c "${config}" "${decoder_config}" \
      -i "${prefix}" \
      -o "${prefix}.nbest" \
      --log "${prefix}.log" \
      --n-best \
      -d "${GPUS}" \
      -w "${WORKSPACE}"
done

# Extract best translations from n-best lists w.r.t to the reference.
# It is CPU-only, can be run after translation on a CPU machine.
test -s "${tmp_dir}/file.00.nbest.out" ||
  ls "${tmp_dir}" | grep -E "^file\.[0-9]+$" | shuf |
  parallel --no-notice -k -j "$(nproc)" \
    "python ${WORKDIR}/pipeline/translate/bestbleu.py -i {}.nbest -r {}.ref -m bleu > {}.nbest.out" \
    2>"${tmp_dir}/debug.txt"

# Collect translations.
test -s "${output_path}" || cat "${tmp_dir}"/file.??.nbest.out | pigz >"${output_path}"

# Source and artificial target files must have the same number of sentences,
# otherwise collect the data manually.
echo "### sentences ${corpus_src} vs ${output_path}"
src_len=$(pigz -dc "${corpus_src}" | wc -l)
trg_len=$(pigz -dc "${output_path}" | wc -l)
if [ "${src_len}" != "${trg_len}" ]; then
  echo "### Error: length of ${corpus_src} ${src_len} is different from ${output_path} ${trg_len}"
  exit 1
fi

rm -rf ${tmp_dir}

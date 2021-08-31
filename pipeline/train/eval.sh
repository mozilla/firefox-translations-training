#!/bin/bash
##
# Evaluate a model.
#
# Usage:
#   bash eval.sh model_dir [src] [trg]
#

set -x
set -euo pipefail

echo "###### Evaluation of a model"

test -v GPUS
test -v MARIAN
test -v WORKSPACE

model_dir=$1
datasets_dir=$2
src="${3:-${SRC}}"
trg="${4:-${TRG}}"


config="${model_dir}/model.npz.best-bleu-detok.npz.decoder.yml"
eval_dir="${model_dir}/eval"

echo "### Checking model files"
test -e "${config}" || exit 1
mkdir -p "${eval_dir}"

echo "### Evaluating a model ${model_dir}"
for src_path in "${datasets_dir}"/*."${src}"; do
  prefix=$(basename "${src_path}" ".${src}")
  echo "### Evaluating ${prefix} ${src}-${trg}"

  test -s "${eval_dir}/${prefix}.${trg}.bleu" ||
    tee "${eval_dir}/${prefix}.${src}" < "${src_path}" |
    "${MARIAN}"/marian-decoder \
      -c "${config}" \
      -w "${WORKSPACE}" \
      --quiet \
      --quiet-translation \
      --log "${eval_dir}/${prefix}.log" \
      -d ${GPUS} |
    tee "${eval_dir}/${prefix}.${trg}" |
    sacrebleu -d -l "${src}-${trg}" "${datasets_dir}/${prefix}.${trg}"  |
    tee "${eval_dir}/${prefix}.${trg}.bleu"

  test -e "${eval_dir}/${prefix}.${trg}.bleu" || exit 1
done


echo "###### Done: Evaluation of a model"

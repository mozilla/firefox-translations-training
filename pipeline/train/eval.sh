#!/bin/bash
##
# Evaluate a model.
#

set -x
set -euo pipefail

echo "###### Evaluation of a model"

test -v GPUS
test -v MARIAN
test -v WORKSPACE

eval_dir=$1
datasets_dir=$2
src=$3
trg=$4
models=( "${@:5}" )


mkdir -p "${eval_dir}"

echo "### Evaluating the model"
for src_path in "${datasets_dir}"/*."${src}.gz"; do
  prefix=$(basename "${src_path}" ".${src}.gz")
  echo "### Evaluating ${prefix} ${src}-${trg}"

  pigz -dc "${datasets_dir}/${prefix}.${TRG}.gz" > "${eval_dir}/${prefix}.${TRG}.ref"

  test -s "${eval_dir}/${prefix}.${trg}.bleu" ||
    pigz -dc "${src_path}" |
    tee "${eval_dir}/${prefix}.${src}" |
    "${MARIAN}"/marian-decoder \
      -m "${models[@]}" \
      -c "${models[0]}.decoder.yml" \
      -w "${WORKSPACE}" \
      --quiet \
      --quiet-translation \
      --log "${eval_dir}/${prefix}.log" \
      -d ${GPUS} |
    tee "${eval_dir}/${prefix}.${trg}" |
    sacrebleu -d --score-only -l "${src}-${trg}" "${eval_dir}/${prefix}.${TRG}.ref"  |
    tee "${eval_dir}/${prefix}.${trg}.bleu"

  test -e "${eval_dir}/${prefix}.${trg}.bleu" || exit 1
done


echo "###### Done: Evaluation of a model"

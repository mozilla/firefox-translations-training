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
#todo: work with gz corpus
echo "### Evaluating the model"
for src_path in "${datasets_dir}"/*."${src}"; do
  prefix=$(basename "${src_path}" ".${src}")
  echo "### Evaluating ${prefix} ${src}-${trg}"

  test -s "${eval_dir}/${prefix}.${trg}.bleu" ||
    tee "${eval_dir}/${prefix}.${src}" < "${src_path}" |
    "${MARIAN}"/marian-decoder \
      -m "${models[@]}" \
      -c "${models[0]}/decoder.yml" \
      -w "${WORKSPACE}" \
      --quiet \
      --quiet-translation \
      --log "${eval_dir}/${prefix}.log" \
      -d ${GPUS} |
    tee "${eval_dir}/${prefix}.${trg}" |
    sacrebleu -d --score-only -l "${src}-${trg}" "${datasets_dir}/${prefix}.${trg}"  |
    tee "${eval_dir}/${prefix}.${trg}.bleu"

  test -e "${eval_dir}/${prefix}.${trg}.bleu" || exit 1
done


echo "###### Done: Evaluation of a model"

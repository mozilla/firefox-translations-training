#!/bin/bash
##
# Evaluate a quantized model on CPU.
#

set -x
set -euo pipefail

echo "###### Evaluation of a quantized model"

test -v MARIAN
test -v SRC
test -v TRG

model_dir=$1
shortlist=$2
datasets_dir=$3
vocab=$4
eval_dir=$5

mkdir -p "${eval_dir}"
#todo: work with gz corpus
echo "### Evaluating a model ${model_dir} on CPU"
for src_path in "${datasets_dir}"/*."${SRC}.gz"; do
  prefix=$(basename "${src_path}" ".${SRC}.gz")
  echo "### Evaluating ${prefix} ${SRC}-${TRG}"

  pigz -dc "${datasets_dir}/${prefix}.${TRG}.gz" > "${eval_dir}/${prefix}.${TRG}.ref"

  test -s "${eval_dir}/${prefix}.${TRG}.bleu" ||
    pigz -dc "${src_path}" |
    tee "${eval_dir}/${prefix}.${SRC}" |
    "${MARIAN}"/marian-decoder \
      -m "${model_dir}/model.intgemm.alphas.bin" \
      -v "${vocab}" "${vocab}" \
      -c "pipeline/quantize/decoder.yml" \
      --quiet \
      --quiet-translation \
      --log "${eval_dir}/${prefix}.log" \
      --shortlist "${shortlist}" false \
      --int8shiftAlphaAll |
    tee "${eval_dir}/${prefix}.${TRG}" |
    sacrebleu -d --score-only -l "${SRC}-${TRG}" "${eval_dir}/${prefix}.${TRG}.ref" |
    tee "${eval_dir}/${prefix}.${TRG}.bleu"

  test -e "${eval_dir}/${prefix}.${TRG}.bleu" || exit 1
done

echo "###### Done: Evaluation of a quantized model"

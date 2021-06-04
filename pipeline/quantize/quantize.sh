#!/bin/bash
##
# Runs quantization of the student model.
#
# Usage:
#   bash quantize.sh corpus_prefix model_dir shortlist devtest_src output_dir
#

set -x
set -euo pipefail

test -v MARIAN
test -v BIN
test -v SRC
test -v TRG

corpus_prefix=$1
model_dir=$2
shortlist=$3
devtest_src=$4
output_dir=$5

mkdir -p "${output_dir}"

model=$model_dir/model-finetune.npz.best-bleu-detok.npz
vocab=$model_dir/vocab.spm

echo "### Decoding a sample test set in order to get typical quantization values"
test -s "${output_dir}/quantmults" ||
  $MARIAN/marian-decoder \
    -m "${model}" -v "${vocab}" "${vocab}" \
    -i "${devtest_src}" -o "${output_dir}/output.${TRG}" \
    --beam-size 1 --mini-batch 32 --maxi-batch 100 --maxi-batch-sort src -w "${WORKSPACE}" -d "${GPUS}" \
    --skip-cost --shortlist "${shortlist}" 50 50 --cpu-threads 1 \
    --quiet --quiet-translation --log "${output_dir}/cpu.newstest2013.log" --dump-quantmult 2>"${output_dir}/quantmults"

echo "### Quantizing"
test -s "${output_dir}/model.alphas.npz" ||
  "${MARIAN}"/../scripts/alphas/extract_stats.py "${output_dir}/quantmults" "${model}" "${output_dir}/model.alphas.npz"
echo "### Converting"
test -s $output_dir/model.intgemm.alphas.bin ||
  $MARIAN/marian-conv \
    -f $output_dir/model.alphas.npz -t $output_dir/model.intgemm.alphas.bin --gemm-type intgemm8

echo "### Translating on CPU"
$MARIAN/marian-decoder \
  -m $output_dir/model.intgemm.alphas.bin -v $vocab $vocab \
  -i speed/newstest2013.$SRC -o speed/cpu.newstest2013.$TRG \
  --beam-size 1 --mini-batch 32 --maxi-batch 100 --maxi-batch-sort src -w ${WORKSPACE} -d ${GPUS} \
  --skip-cost --shortlist lex.s2t.gz 50 50 --cpu-threads 1 \
  --quiet --quiet-translation --log speed/cpu.newstest2013.log --int8shiftAlphaAll

tail -n1 speed/cpu.newstest2013.log
sacrebleu -t wmt13 -l $SRC-$TRG <speed/cpu.newstest2013.$TRG | tee speed/cpu.newstest2013.$TRG.bleu

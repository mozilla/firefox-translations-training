#!/bin/bash
##
# Runs quantization of the student model.
#
# Usage:
#   bash quantize.sh corpus_prefix vocab_path output_dir
#

set -x
set -euo pipefail


test -v MARIAN
test -v BIN
tests -v SRC
test -v TRG

corpus_prefix=$1
vocab_path=$2
dir=$3

# TODO

mkdir -p speed

sacrebleu -t wmt13 -l $SRC-$TRG --echo src > speed/newstest2013.$SRC

if [ ! -f speed/model.intgemm.alphas.bin ]; then

test -e speed/model.alphas.npz || $MARIAN/marian-decoder $@ \
    --relative-paths -m finetune/model-finetune.npz.best-bleu-detok.npz -v vocab.spm vocab.spm \
    -i speed/newstest2013.$SRC -o speed/cpu.newstest2013.$TRG \
    --beam-size 1 --mini-batch 32 --maxi-batch 100 --maxi-batch-sort src -w 128 \
    --skip-cost --shortlist lex.s2t.gz 50 50 --cpu-threads 1 \
    --quiet --quiet-translation --log speed/cpu.newstest2013.log --dump-quantmult  2> speed/quantmults

test -e speed/model.alphas.npz || $MARIAN/../scripts/alphas/extract_stats.py speed/quantmults finetune/model-finetune.npz.best-bleu-detok.npz speed/model.alphas.npz

test -e speed/model.intgemm.alphas.bin || $MARIAN/marian-conv -f speed/model.alphas.npz -t speed/model.intgemm.alphas.bin --gemm-type intgemm8

fi

echo "### Translating wmt13 $SRC-$TRG on CPU"
$MARIAN/marian-decoder $@ \
    --relative-paths -m speed/model.intgemm.alphas.bin -v vocab.spm vocab.spm \
    -i speed/newstest2013.$SRC -o speed/cpu.newstest2013.$TRG \
    --beam-size 1 --mini-batch 32 --maxi-batch 100 --maxi-batch-sort src -w 128 \
    --skip-cost --shortlist lex.s2t.gz 50 50 --cpu-threads 1 \
    --quiet --quiet-translation --log speed/cpu.newstest2013.log --int8shiftAlphaAll

tail -n1 speed/cpu.newstest2013.log
sacrebleu -t wmt13 -l $SRC-$TRG < speed/cpu.newstest2013.$TRG | tee speed/cpu.newstest2013.$TRG.bleu

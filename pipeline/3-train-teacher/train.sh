#!/bin/bash -v
##
# Train teacher model.
#
# Usage:
#   bash train.sh
#

set -x
set -euo pipefail


GPUS=${GPUS:-"0 1 2 3"}
MARIAN=${MARIAN:-"../../marian-dev/build"}
SRC=${SRC:-es}
TRG=${TRG:-en}
WORKSPACE=${WORKSPACE:-14000}

test -e ${DATA_DIR}/clean/corpus.$SRC.gz || exit 1
test -e ${DATA_DIR}/clean/corpus.$TRG.gz || exit 1

test -e ${DATA_DIR}/original/devset.${SRC} || exit 1
test -e ${DATA_DIR}/original/devset.${TRG} || exit 1

mkdir -p tmp
dir=${MODELS_DIR}/teacher
mkdir -p $dir

echo "Training teacher model"

$MARIAN/marian \
    --model ${dir}/model.npz -c teacher.yml \
    --train-sets ${DATA_DIR}/clean/corpus.{$SRC,$TRG}.gz -T ./tmp --shuffle-in-ram \
    --vocabs ${dir}/vocab.spm ${dir}/vocab.spm --dim-vocabs 32000 32000 \
    --max-length 100 \
    --beam-size 6 --normalize 0.6 \
    --transformer-dropout 0.1 --label-smoothing 0.1 --exponential-smoothing \
    --mini-batch-fit -w $WORKSPACE --maxi-batch 1000 --devices $GPUS --sync-sgd  \
    --learn-rate 0.0003 --lr-warmup 16000 --lr-decay-inv-sqrt 16000 --lr-report \
    --cost-type ce-mean-words \
    --optimizer-params 0.9 0.98 1e-09 --clip-norm 5 \
    --valid-freq 5000 --save-freq 5000 --disp-freq 500 --disp-first 10 \
    --valid-metrics bleu-detok ce-mean-words \
    --valid-sets ${DATA_DIR}/original/devset.{$SRC,$TRG} --valid-translation-output ${dir}/devset.out --quiet-translation \
    --valid-mini-batch 64 --beam-size 12 --normalize 1 \
    --early-stopping 10 \
    --overwrite --keep-best \
    --log ${dir}/train.log --valid-log ${dir}/valid.log \

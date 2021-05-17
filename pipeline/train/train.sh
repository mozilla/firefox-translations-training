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

test -e ${DATA_DIR}/clean/corpus.$SRC.clean.gz || exit 1
test -e ${DATA_DIR}/clean/corpus.$TRG.clean.gz || exit 1

test -e ${DATA_DIR}/original/devset.${SRC}.gz || exit 1
test -e ${DATA_DIR}/original/devset.${TRG}.gz || exit 1

mkdir -p tmp
dir=${MODELS_DIR}/teacher
mkdir -p $dir

echo "Training teacher model"

$MARIAN/marian \
    --model ${dir}/model.npz -c ${WORKDIR}/pipeline/3-train-teacher/teacher.yml \
    --train-sets ${DATA_DIR}/clean/corpus.{$SRC,$TRG}.clean.gz -T tmp --shuffle-in-ram \
    --vocabs ${dir}/vocab.spm ${dir}/vocab.spm \
    -w $WORKSPACE \
    --devices $GPUS --sync-sgd \
    --valid-metrics bleu-detok ce-mean-words \
    --valid-sets ${DATA_DIR}/original/devset.{$SRC,$TRG}.gz --valid-translation-output ${dir}/devset.out \
    --quiet-translation \
    --overwrite --keep-best \
    --log ${dir}/train.log --valid-log ${dir}/valid.log \

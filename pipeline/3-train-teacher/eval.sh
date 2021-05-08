#!/bin/bash -v
##
# Evaluate teacher model.
#
# Usage:
#   bash eval.sh [datasets...]
#

set -x
set -euo pipefail

marian=${MARIAN:-"../../marian-dev/build"}
workspace=${WORKSPACE:-4000}
test_datasets=${TEST_DATASETS:-$@}
test -v SRC
test -v TRG
test -v GPUS

echo "Checking model files"
test -e ${teacher_dir}/model.npz.best-bleu-detok.npz.decoder.yml || exit 1

teacher_dir=${MODELS_DIR}/teacher
eval_dir=${teacher_dir}/eval
mkdir -p $dir

echo "Evaluating teacher model"

for prefix in ${test_datasets}; do
    echo "### Evaluating $prefix $SRC-$TRG"
    sacrebleu -t $prefix -l $SRC-$TRG --echo src \
        | tee ${eval_dir}/$prefix.$SRC \
        | $marian/marian-decoder -c ${teacher_dir}/model.npz.best-bleu-detok.npz.decoder.yml -w ${workspace} \
                                 --quiet --log ${eval_dir}/$prefix.log -d $GPUS \
        | tee ${eval_dir}/$prefix.$TRG \
        | sacrebleu -d -t $prefix -l $SRC-$TRG \
        | tee ${eval_dir}/$prefix.$TRG.bleu

    test -e ${eval_dir}/$prefix.$TRG.bleu || exit 1
done

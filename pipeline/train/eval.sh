#!/bin/bash -v
##
# Evaluate a model.
#
# Usage:
#   bash eval.sh model_dir [datasets...]
#

set -x
set -euo pipefail

marian=${MARIAN:-"../../marian-dev/build"}
workspace=${WORKSPACE:-4000}
test_datasets=${TEST_DATASETS:-${@:2}}

model_dir=$1

test -v SRC
test -v TRG
test -v GPUS

eval_dir=${model_dir}/eval

echo "Checking model files"
test -e ${model_dir}/model.npz.best-bleu-detok.npz.decoder.yml || exit 1

mkdir -p $eval_dir

echo "Evaluating a model ${model_dir}"

for prefix in ${test_datasets}; do
    echo "### Evaluating $prefix $SRC-$TRG"
    sacrebleu -t $prefix -l $SRC-$TRG --echo src \
        | tee ${eval_dir}/$prefix.$SRC \
        | $marian/marian-decoder -c ${model_dir}/model.npz.best-bleu-detok.npz.decoder.yml -w ${workspace} \
                                 --quiet  --quiet-translation --log ${eval_dir}/$prefix.log -d $GPUS \
        | tee ${eval_dir}/$prefix.$TRG \
        | sacrebleu -d -t $prefix -l $SRC-$TRG \
        | tee ${eval_dir}/$prefix.$TRG.bleu

    test -e ${eval_dir}/$prefix.$TRG.bleu || exit 1
done

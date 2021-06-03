#!/bin/bash -v
##
# Evaluate a model.
#
# Usage:
#   bash eval.sh model_dir [src] [trg] [datasets...]
#

set -x
set -euo pipefail

test -v GPUS
test -v MARIAN
test -v WORKSPACE

model_dir=$1
src="${2:-$SRC}"
trg="${3:-$TRG}"
datasets=${@:4}
test_datasets=${datasets:-$TEST_DATASETS}


eval_dir=${model_dir}/eval

echo "Checking model files"
test -e ${model_dir}/model.npz.best-bleu-detok.npz.decoder.yml || exit 1

mkdir -p $eval_dir

echo "Evaluating a model ${model_dir}"

for prefix in ${test_datasets}; do
    echo "### Evaluating $prefix $src-$trg"
    sacrebleu -t $prefix -l $src-$trg --echo src \
        | tee ${eval_dir}/$prefix.$src \
        | $MARIAN/marian-decoder -c ${model_dir}/model.npz.best-bleu-detok.npz.decoder.yml -w ${WORKSPACE} \
                                 --quiet  --quiet-translation --log ${eval_dir}/$prefix.log -d $GPUS \
        | tee ${eval_dir}/$prefix.$trg \
        | sacrebleu -d -t $prefix -l $src-$trg \
        | tee ${eval_dir}/$prefix.$trg.bleu

    test -e ${eval_dir}/$prefix.$trg.bleu || exit 1
done

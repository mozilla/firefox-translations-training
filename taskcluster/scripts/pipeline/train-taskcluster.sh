#!/bin/bash

set -x
set -euo pipefail

pushd `dirname $0`/../../.. &>/dev/null
VCS_ROOT=$(pwd)
popd &>/dev/null

if [ "$#" -lt 10 ]; then
    echo "Usage: $0 <model_type> <training_type> <src_locale> <trg_locale> <train_set_prefix> <valid_set_prefix> <model_dir> <best_model_metric> <alignments> <pretrained_model_mode> <pretrained_model_type> [extra_params...]"
    exit 1
fi

model_type=$1
training_type=$2
src=$3
trg=$4
train_set_prefix=$5
valid_set_prefix=$6
model_dir=$7
best_model_metric=$8
alignments=$9
seed=${10}
pretrained_model_mode=${11}
pretrained_model_type=${12}
extra_params=( "${@:13}" )

if [ "$pretrained_model_mode" != "use" ]; then
    # MOZ_FETCHES_DIR is not required for the "use" pretrained model mode
    [[ -v MOZ_FETCHES_DIR ]] || { echo "MOZ_FETCHES_DIR is not set"; exit 1; }
fi

case "$pretrained_model_mode" in
    "use")
        echo "The training mode is 'use', using existing model without further training."
        exit 0
        ;;
    "continue"|"init"|"None")
        if [ "$pretrained_model_mode" == "None" ]; then
            vocab="$MOZ_FETCHES_DIR/vocab.spm"
        else
            vocab="$TASK_WORKDIR/artifacts/vocab.spm"
        fi

        export MARIAN=$MOZ_FETCHES_DIR

        if [ "$pretrained_model_mode" == "init" ]; then
            extra_params+=("--pretrained-model" "$TASK_WORKDIR/artifacts/final.model.npz.best-$best_model_metric.npz" "--no-restore-corpus")
        fi
        $VCS_ROOT/pipeline/train/train.sh \
        "$model_type" \
        "$training_type" \
        "$src" \
        "$trg" \
        "$train_set_prefix" \
        "$valid_set_prefix" \
        "$model_dir" \
        "$vocab" \
        "$best_model_metric" \
        "$alignments" \
        "$seed" \
        "${extra_params[@]}"
        if [ "$pretrained_model_mode" == "None" ]; then
            cp "$vocab" "$model_dir"
        fi
        ;;
esac

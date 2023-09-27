#!/bin/bash

set -x
set -euo pipefail

[[ -v MOZ_FETCHES_DIR ]] || { echo "MOZ_FETCHES_DIR is not set"; exit 1; }
[[ -v VCS_PATH ]] || { echo "VCS_PATH is not set"; exit 1; }

if [ "$#" -lt 11 ]; then
    echo "Usage: $0 <model_type> <training_type> <src_locale> <trg_locale> <train_set_prefix> <valid_set_prefix> <model_dir> <vocab> <best_model_metric> <pretrained_model_mode> <pretrained_model_type> [extra_params...]"
    exit 1
fi

model_type=$1
training_type=$2
src=$3
trg=$4
train_set_prefix=$5
valid_set_prefix=$6
model_dir=$7
vocab=$8
best_model_metric=$9
pretrained_model_mode=${10}
pretrained_model_type=${11}
extra_params=( "${@:12}" )

echo "$pretrained_model_mode"
echo "$pretrained_model_type"

export MARIAN=$MOZ_FETCHES_DIR

case "$pretrained_model_mode" in
    "use")
        echo "The training mode is 'use', using existing model without further training."
        exit 0
        ;;
    "continue")
        $VCS_PATH/pipeline/train/train.sh \
        "$model_type" \
        "$training_type" \
        "$src" \
        "$trg" \
        "$train_set_prefix" \
        "$valid_set_prefix" \
        "$model_dir" \
        "$vocab" \
        "$best_model_metric" \
        "${extra_params[@]}"
        ;;
    "init")
        extra_params+=("--pretrained-model" "./artifacts/final.model.npz.best-chrf.npz")
        $VCS_PATH/pipeline/train/train.sh \
        "$model_type" \
        "$training_type" \
        "$src" \
        "$trg" \
        "$train_set_prefix" \
        "$valid_set_prefix" \
        "$model_dir" \
        "$vocab" \
        "$best_model_metric" \
        "${extra_params[@]}"
        ;;
    *)
        echo "Unknown pretrained_model_mode: $pretrained_model_mode"
        exit 1
        ;;
esac

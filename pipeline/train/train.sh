#!/bin/bash
##
# Train a model.
#
# Usage:
#   bash train.sh model_config training_config src trg data_dir train_set_prefix \
#                 valid_set_prefix model_dir [extra_marian_params...]
#

set -x
set -euo pipefail

echo "###### Training a model"

#TODO too many positional args here, replace with names args

model_config=$1
training_config=$2
src=$3
trg=$4
train_set_prefix=$5
valid_set_prefix=$6
model_dir=$7
vocab=$8
extra_params=( "${@:9}" )

test -v GPUS
test -v MARIAN
test -v WORKSPACE

mkdir -p "${model_dir}/tmp"

echo "### Training ${model_dir}"

# if doesn't fit in RAM, remove --shuffle-in-ram and add --shuffle batches

"${MARIAN}/marian" \
  --model "${model_dir}/model.npz" \
  -c "${model_config}" "${training_config}" \
  --train-sets "${train_set_prefix}".{"${src}","${trg}"}.gz \
  -T "${model_dir}/tmp" \
  --shuffle-in-ram \
  --vocabs "${vocab}" "${vocab}" \
  -w "${WORKSPACE}" \
  --devices ${GPUS} \
  --sync-sgd \
  --valid-metrics bleu-detok ce-mean-words perplexity \
  --valid-sets "${valid_set_prefix}".{"${src}","${trg}"}.gz \
  --valid-translation-output "${model_dir}/devset.out" \
  --quiet-translation \
  --overwrite \
  --keep-best \
  --log "${model_dir}/train.log" \
  --valid-log "${model_dir}/valid.log" \
  "${extra_params[@]}"

echo "### Model training is completed: ${model_dir}"
echo "###### Done: Training a model"

#!/bin/bash
##
# Train a model.
#

set -x
set -euo pipefail

echo "###### Training a model"

model_type=$1
training_type=$2
src=$3
trg=$4
train_set_prefix=$5
valid_set_prefix=$6
model_dir=$7
vocab=$8
best_model_metric=$9
extra_params=( "${@:10}" )

ARTIFACT_EXT="${ARTIFACT_EXT:-gz}"

test -v GPUS
test -v MARIAN
test -v WORKSPACE

cd "$(dirname "${0}")"
mkdir -p "${model_dir}/tmp"

all_model_metrics=(chrf ce-mean-words bleu-detok)

echo "### Training ${model_dir}"

# if doesn't fit in RAM, remove --shuffle-in-ram and add --shuffle batches

# Marian doesn't support zst natively; we need to decompress before passing them
# along.
if [ "${ARTIFACT_EXT}" = "zst" ]; then
  zstdmt --rm -d "${train_set_prefix}.${src}.${ARTIFACT_EXT}"
  zstdmt --rm -d "${train_set_prefix}.${trg}.${ARTIFACT_EXT}"
  zstdmt --rm -d "${valid_set_prefix}.${src}.${ARTIFACT_EXT}"
  zstdmt --rm -d "${valid_set_prefix}.${trg}.${ARTIFACT_EXT}"
  ARTIFACT_EXT=""
else
  ARTIFACT_EXT=".gz"
fi

"${MARIAN}/marian" \
  --model "${model_dir}/model.npz" \
  -c "configs/model/${model_type}.yml" "configs/training/${model_type}.${training_type}.yml" \
  --train-sets "${train_set_prefix}".{"${src}","${trg}"}${ARTIFACT_EXT} \
  -T "${model_dir}/tmp" \
  --shuffle-in-ram \
  --vocabs "${vocab}" "${vocab}" \
  -w "${WORKSPACE}" \
  --devices ${GPUS} \
  --sharding local \
  --sync-sgd \
  --valid-metrics "${best_model_metric}" ${all_model_metrics[@]/$best_model_metric} \
  --valid-sets "${valid_set_prefix}".{"${src}","${trg}"}${ARTIFACT_EXT} \
  --valid-translation-output "${model_dir}/devset.out" \
  --quiet-translation \
  --overwrite \
  --keep-best \
  --log "${model_dir}/train.log" \
  --valid-log "${model_dir}/valid.log" \
  "${extra_params[@]}"

cp "${model_dir}/model.npz.best-${best_model_metric}.npz" "${model_dir}/final.model.npz.best-${best_model_metric}.npz"
cp "${model_dir}/model.npz.best-${best_model_metric}.npz.decoder.yml" "${model_dir}/final.model.npz.best-${best_model_metric}.npz.decoder.yml"

echo "### Model training is completed: ${model_dir}"
echo "###### Done: Training a model"

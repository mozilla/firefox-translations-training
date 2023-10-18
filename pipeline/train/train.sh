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
# comma separated prefixes to datasets for curriculum learning
train_set_prefixes=$5
valid_set_prefix=$6
model_dir=$7
vocab=$8
best_model_metric=$9
alignments=${10}
extra_params=( "${@:11}" )

COMPRESSION_CMD="${COMPRESSION_CMD:-pigz}"
ARTIFACT_EXT="${ARTIFACT_EXT:-gz}"

test -v GPUS
test -v MARIAN
test -v WORKSPACE

cd "$(dirname "${0}")"
mkdir -p "${model_dir}/tmp"

all_model_metrics=(chrf ce-mean-words bleu-detok)

echo "### Preparing tsv datasets and config"

# Generate a new OpusTrainer config based on a template to fill paths of the datasets
new_config="${model_dir}/config.opustrainer.yml"
cp "configs/opustrainer/${model_type}.yml" "${new_config}"

# Iterate over the training sets
# split the input string into an array
IFS=',' read -ra elements <<< "${train_set_prefixes}"
# loop through the array and get both value and index
for index in "${!elements[@]}"; do
    train_set_prefix="${elements[index]}"
    tsv_dataset="${train_set_prefix}.${src}${trg}.tsv"
    # OpusTrainer supports only tsv
    paste <(${COMPRESSION_CMD} -dc "${train_set_prefix}.${src}.${ARTIFACT_EXT}") \
          <(${COMPRESSION_CMD} -dc "${train_set_prefix}.${trg}.${ARTIFACT_EXT}") \
          >"${tsv_dataset}"
    # replace the dataset path in the template in place
    sed -i -e "s#<dataset${index}>#${tsv_dataset}#g" "${new_config}"
done

# if the training set is a tsv, validation set also has to be a tsv
echo "### Converting validation sets to tsv"
valid_tsv_dataset="${valid_set_prefix}.${src}${trg}.tsv"
paste <(${COMPRESSION_CMD} -dc "${valid_set_prefix}.${src}.${ARTIFACT_EXT}") \
      <(${COMPRESSION_CMD} -dc "${valid_set_prefix}.${trg}.${ARTIFACT_EXT}") \
      >"${valid_tsv_dataset}"

# Add alignments to tsv if provided
# when using tsv, marian requires --guided-alignments argument to be an index of the alignments in the tsv file
if [ "${alignments}" != "None" ] ; then
  echo "### Adding alignments ${alignments} to the training dataset"
  paste "${tsv_dataset}" <(${COMPRESSION_CMD} -dc "${alignments}") > corpus_with_alignments.tsv
  mv corpus_with_alignments.tsv "${tsv_dataset}"
  extra_params+=("--guided-alignment" "2")
fi

echo "### Training ${model_dir}"
# OpusTrainer reads the datasets, shuffles, augments them and feeds to stdin of Marian
# suppress logging warnings for empty fields
# TODO: opustrainer complains on Marian --log option
opustrainer-train \
  --config "${new_config}" \
  --log-file "${model_dir}/opustrainer.log" \
  --log-level ERROR \
  "${MARIAN}/marian" \
    --model "${model_dir}/model.npz" \
    -c "configs/model/${model_type}.yml" "configs/training/${model_type}.${training_type}.yml" \
    -T "${model_dir}/tmp" \
    --vocabs "${vocab}" "${vocab}" \
    -w "${WORKSPACE}" \
    --devices ${GPUS} \
    --valid-metrics "${best_model_metric}" ${all_model_metrics[@]/$best_model_metric} \
    --valid-sets "${valid_tsv_dataset}" \
    --valid-translation-output "${model_dir}/devset.out" \
    --valid-log "${model_dir}/valid.log" \
    --shuffle batches \
    --sentencepiece-alphas 0.1 \
    --no-restore-corpus \
    --sharding local \
    --sync-sgd \
    --quiet-translation \
    --overwrite \
    --keep-best \
    --tsv \
    "${extra_params[@]}"

cp "${model_dir}/model.npz.best-${best_model_metric}.npz" "${model_dir}/final.model.npz.best-${best_model_metric}.npz"
cp "${model_dir}/model.npz.best-${best_model_metric}.npz.decoder.yml" "${model_dir}/final.model.npz.best-${best_model_metric}.npz.decoder.yml"

echo "### Model training is completed: ${model_dir}"
echo "###### Done: Training a model"

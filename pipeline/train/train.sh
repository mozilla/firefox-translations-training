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
# comma separated alignment paths that correspond to each training dataset
# or None to train without alignments
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
IFS=',' read -ra datasets <<< "${train_set_prefixes}"
IFS=',' read -ra alns <<< "${alignments}"
# loop through the array and get both value and index
for index in "${!datasets[@]}"; do
    train_set_prefix="${datasets[index]}"
    # OpusTrainer supports only tsv and gzip
    # TODO: pigz is not found
    tsv_dataset="${train_set_prefix}.${src}${trg}.tsv" #.gz"

    if [ "${alignments}" != "None" ] ; then
      train_aln="${alns[index]}"
      # alignments are currently used only for student that uses one stage of training
      echo "### Generating tsv dataset with alignments ${alignments}"
      paste <(${COMPRESSION_CMD} -dc "${train_set_prefix}.${src}.${ARTIFACT_EXT}") \
            <(${COMPRESSION_CMD} -dc "${train_set_prefix}.${trg}.${ARTIFACT_EXT}") \
            <(${COMPRESSION_CMD} -dc "${train_aln}") \
            >"${tsv_dataset}"
      rm "${train_aln}"
      # when using tsv, marian requires --guided-alignments argument to be an index of the alignments in the tsv file
      extra_params+=("--guided-alignment" "2")
    else
      echo "### Generating tsv dataset"
      # OpusTrainer supports only tsv and gzip
      paste <(${COMPRESSION_CMD} -dc "${train_set_prefix}.${src}.${ARTIFACT_EXT}") \
            <(${COMPRESSION_CMD} -dc "${train_set_prefix}.${trg}.${ARTIFACT_EXT}") \
            >"${tsv_dataset}"
    fi
    # free disk space
    rm "${train_set_prefix}.${src}.${ARTIFACT_EXT}"
    rm "${train_set_prefix}.${trg}.${ARTIFACT_EXT}"
    # replace the dataset path in the template in place
    sed -i -e "s#<dataset${index}>#${tsv_dataset}#g" "${new_config}"
done

# Replace the path to vocab (required for alignments to work)
sed -i -e "s#<vocab>#${vocab}#g" "${new_config}"

# if the training set is a tsv, validation set also has to be a tsv
echo "### Converting validation sets to tsv"
valid_tsv_dataset="${valid_set_prefix}.${src}${trg}.tsv"
paste <(${COMPRESSION_CMD} -dc "${valid_set_prefix}.${src}.${ARTIFACT_EXT}") \
      <(${COMPRESSION_CMD} -dc "${valid_set_prefix}.${trg}.${ARTIFACT_EXT}") \
      >"${valid_tsv_dataset}"


echo "### Training ${model_dir}"
# OpusTrainer reads the datasets, shuffles, augments them and feeds to stdin of Marian
opustrainer-train \
  --config "${new_config}" \
  --log-file "${model_dir}/opustrainer.log" \
  --log-level INFO \
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
    --log "${model_dir}/train.log" \
    --shuffle batches \
    --sentencepiece-alphas 0.1 \
    --no-restore-corpus \
    --valid-reset-stalled \
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

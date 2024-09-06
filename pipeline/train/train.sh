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
# for example path1/corpus,path2/mono
train_set_prefixes=$5
valid_set_prefix=$6
model_dir=$7
vocab=$8
best_model_metric=$9
# comma separated alignment paths that correspond to each training dataset
# (required for Tags modifier and guided alignments for student training)
# or None to train without alignments
alignments=${10}
# random seed, UINT
seed=${11}
teacher_mode=${12}
extra_params=( "${@:13}" )

test -v GPUS
test -v MARIAN
test -v WORKSPACE

cd "$(dirname "${0}")"
mkdir -p "${model_dir}/tmp"

all_model_metrics=(chrf ce-mean-words bleu-detok)

echo "### Preparing tsv datasets and config"

# Generate a new OpusTrainer config based on a template to fill paths of the datasets
new_config="${model_dir}/config.opustrainer.yml"
if [ "${model_type}" == "teacher" ] ; then
  echo "### Using teacher training mode: ${teacher_mode}"
  cp "configs/opustrainer/${model_type}.${teacher_mode}.yml" "${new_config}"
else
  cp "configs/opustrainer/${model_type}.yml" "${new_config}"
fi

# Iterate over the training sets
# split the input string into an array
IFS=',' read -ra datasets <<< "${train_set_prefixes}"
IFS=',' read -ra alns <<< "${alignments}"
# loop through the array and get both value and index
for index in "${!datasets[@]}"; do
    train_set_prefix="${datasets[index]}"
    # OpusTrainer supports only tsv and gzip
    # TODO: pigz is not installed on the generic Taskcluster worker, so we use datasets in decompressed mode for now
    tsv_dataset="${train_set_prefix}.${src}${trg}.tsv" #.gz"

    if [ "${alignments}" != "None" ] ; then
      train_aln="${alns[index]}"

      echo "### Generating tsv dataset with alignments ${alignments}"
      paste <(zstdmt -dc "${train_set_prefix}.${src}.zst") \
            <(zstdmt -dc "${train_set_prefix}.${trg}.zst") \
            <(zstdmt -dc "${train_aln}") \
            >"${tsv_dataset}"
      rm "${train_aln}"
      # grep returns exit code 1 if there are no matches
      empty_aln_num=$(cut -f3 "${tsv_dataset}" | grep -Fxc "") || true
      echo "### Number of empty alignments for ${train_aln}: ${empty_aln_num}"
    else
      echo "### Generating tsv dataset"
      # OpusTrainer supports only tsv and gzip
      paste <(zstdmt -dc "${train_set_prefix}.${src}.zst") \
            <(zstdmt -dc "${train_set_prefix}.${trg}.zst") \
            >"${tsv_dataset}"
    fi
    # free disk space
    rm "${train_set_prefix}.${src}.zst"
    rm "${train_set_prefix}.${trg}.zst"
    # replace the dataset path in the template in place
    sed -i -e "s#<dataset${index}>#${tsv_dataset}#g" "${new_config}"
done

# Replace the path to vocab
# OpusTrainer uses space tokenized alignments for inline noise (Tags modifier)
# then detokenizes them and coverts to SentencePiece tokenized ones using the vocab to feed to Marian
sed -i -e "s#<vocab>#${vocab}#g" "${new_config}"
# Replace source and target languages. This can be useful for custom detokenizer parameter in Tags
sed -i -e "s#<src>#${src}#g" "${new_config}"
sed -i -e "s#<trg>#${trg}#g" "${new_config}"
# Replace the random seed for teachers
sed -i -e "s#<seed>#${seed}#g" "${new_config}"

# if the training set is a tsv, validation set also has to be a tsv
echo "### Converting validation sets to tsv"
valid_tsv_dataset="${valid_set_prefix}.${src}${trg}.tsv"
paste <(zstdmt -dc "${valid_set_prefix}.${src}.zst") \
      <(zstdmt -dc "${valid_set_prefix}.${trg}.zst") \
      >"${valid_tsv_dataset}"


# we run a CPU version of Marian in tests and it does not work with these arguments
if [[ -z ${USE_CPU+x} ]]; then
  extra_params+=('--sharding')
  extra_params+=('local')
fi

# Enable log & metrics publication only when the tracking script is available
# and not running in unit tests
if ! command -v parse_tc_logs &> /dev/null
then
  echo "### Weight & Biases publication script is not available."
  PARSER=cat
elif [ ! -z ${TEST_ARTIFACTS+x} ];
then
  echo "### Weight & Biases publication is disabled for unit tests."
  PARSER=cat
else
  echo "### Weight & Biases publication is available."
  PARSER="parse_tc_logs --from-stream --publish-group-logs -v"
fi

echo "### Training ${model_dir}"
# OpusTrainer reads the datasets, shuffles, augments them and feeds to stdin of Marian
opustrainer-train \
  --config "${new_config}" \
  --log-file "${model_dir}/opustrainer.log" \
  --log-level ERROR \
  "${MARIAN}/marian" \
    --model "${model_dir}/model.npz" \
    --config "configs/model/${model_type}.yml" "configs/training/${model_type}.${training_type}.yml" \
    --tempdir "${model_dir}/tmp" \
    --vocabs "${vocab}" "${vocab}" \
    --workspace "${WORKSPACE}" \
    --devices ${GPUS} \
    --valid-metrics "${best_model_metric}" ${all_model_metrics[@]/$best_model_metric} \
    --valid-sets "${valid_tsv_dataset}" \
    --valid-translation-output "${model_dir}/devset.out" \
    --valid-log "${model_dir}/valid.log" \
    --log "${model_dir}/train.log" \
    --shuffle batches \
    --no-restore-corpus \
    --valid-reset-stalled \
    --sync-sgd \
    --quiet-translation \
    --overwrite \
    --keep-best \
    --tsv \
    --seed ${seed} \
    "${extra_params[@]}" 2>&1 | $PARSER

cp "${model_dir}/model.npz.best-${best_model_metric}.npz" "${model_dir}/final.model.npz.best-${best_model_metric}.npz"
cp "${model_dir}/model.npz.best-${best_model_metric}.npz.decoder.yml" "${model_dir}/final.model.npz.best-${best_model_metric}.npz.decoder.yml"

echo "### Model training is completed: ${model_dir}"
echo "###### Done: Training a model"

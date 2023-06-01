#!/bin/bash
##
# Downloads a pretrained opus mt (or tatoeba-challenge) model
#

set -x
set -euo pipefail

echo "###### Downloading pretrained opus model"

download_url=$1

model_dir=$2
best_model=$3
source_lang=$4
target_lang=$5

#if download url is best, find the best model from list
if [[ $download_url = "best" ]]
then
    model_list="${model_dir}/released-model-results.txt"
    wget -O ${model_list} "https://raw.githubusercontent.com/Helsinki-NLP/Tatoeba-Challenge/master/models/released-model-results.txt"
    download_url=$(grep -P -m 1 "^${source_lang}-${target_lang}" ${model_list} | cut -f 4) 
    echo "###### Using best ${source_lang}-${target_lang} model ${download_url}"
fi

model_zip=${download_url##*/}
archive_path="${model_dir}/${model_zip}"

wget -O "${archive_path}" "${download_url}"

cd ${model_dir}
unzip -j -o "${archive_path}"
rm ${archive_path}

model_file=$(ls *.npz)
vocab_file=$(ls *vocab.yml)
#Create a soft link for the model with the name that the workflow expects 
ln -s $model_file ${best_model}
#Also create a standard name link for the vocab
ln -s $vocab_file "vocab.yml"


echo "###### Done: Downloading and extracting opus mt model"

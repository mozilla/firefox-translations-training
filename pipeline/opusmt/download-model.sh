#!/bin/bash
##
# Downloads a pretrained opus mt (or tatoeba-challenge) model
#

set -x
set -euo pipefail

echo "###### Downloading pretrained opus model"

download_url=$1
backward_dir=$2
best_model=$3
model_zip=${download_url##*/}

archive_path="${backward_dir}/${model_zip}"

wget -O "${archive_path}" "${download_url}"

cd ${backward_dir}
unzip -j -o "${archive_path}"
rm ${archive_path}

model_file=$(ls *.npz)
vocab_file=$(ls *vocab.yml)
#Create a soft link for the model with the name that the workflow expects 
ln -s $model_file ${best_model}
#Also create a standard name link for the vocab
ln -s $vocab_file "vocab.yml"

#modify preprocess script to remove host check

echo "###### Done: Downloading and extracting opus mt model"

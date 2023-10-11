#!/bin/bash
##
# Applies OPUS-MT preprocessing to corpus
#

set -x
set -euo pipefail


source_file=$1
opusmt_model=$2
source_lang=$3
spm_name=$4
spm_encoder=$5
export PATH=$PATH:$(dirname ${spm_encoder})
model_dir=$(dirname $2)

# When splits are preprocessed, different models need different preprocessing,
# so model index is given. Check for unset parameter.
if [ $# -ge 7 ]; then
    model_index_suffix=".$7"
else
    model_index_suffix=""
fi


#target_lang_token needs to be provided for multilingual models
#first check whether model is multilingual AND preprocessing isdone on source side (never language tags on target side)
if grep -q ">>id<<" "${model_dir}/README.md" && [ ${spm_name} == "source.spm" ]; then
    target_lang_token=$6
    if [ -n "${target_lang_token}" ]; then
        #add space after lang token
        target_lang_token=">>${target_lang_token}<< "
    else
        echo "no target lang token provided"
        exit 1
    fi
else
    target_lang_token=""
fi


if [ "${source_file##*.}" == "gz" ]; then
    echo "source file is gzipped"
    zcat $1 | pipeline/translate/preprocess.sh $3 "${model_dir}/${spm_name}" | sed -e "s/^/${target_lang_token}/" | gzip > ${source_file%%.gz}${model_index_suffix}.opusmt.gz
else
    echo "source file is not gzipped"
    pipeline/translate/preprocess.sh $3 "${model_dir}/${spm_name}" < $1 | sed -e "s/^/${target_lang_token}/" > $1${model_index_suffix}.opusmt
fi 

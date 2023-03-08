#!/bin/bash
##
# Applies OPUS-MT preprocessing to corpus
#

set -x
set -euo pipefail

# add spm_encode to path
export PATH=$(realpath 3rd_party/marian-dev/build/):$PATH

source_file=$1
opusmt_model=$2
source_lang=$3
spm_name=$4
model_dir=$(dirname $2)

if [ "${source_file##*.}" == "gz" ]; then
    echo "source file is gzipped"
    zcat $1 | pipeline/translate/preprocess.sh $3 "${model_dir}/${spm_name}" | gzip > ${source_file%%.gz}.opusmt.gz
else
    echo "source file is not gzipped"
    pipeline/translate/preprocess.sh $3 "${model_dir}/${spm_name}" < $1 > $1.opusmt
fi
 

#!/bin/bash
##
# Use local dataset that is already downloaded.
# Local path prefix without `.<lang_code>.gz` should be specified as a "dataset" parameter
#

set -x
set -euo pipefail

echo "###### Copying local corpus"

src=$1
trg=$2
output_prefix=$3
dataset=$4

cp "${dataset}.${src}.gz" "${output_prefix}.${src}.gz"
cp "${dataset}.${trg}.gz" "${output_prefix}.${trg}.gz"


echo "###### Done: Copying local corpus"

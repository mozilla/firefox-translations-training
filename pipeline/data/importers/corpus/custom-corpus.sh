#!/bin/bash
##
# Use custom dataset that is already downloaded to a local disk
# Local path prefix without `.<lang_code>.gz` should be specified as a "dataset" parameter
#

set -x
set -euo pipefail

echo "###### Copying custom corpus"

src=$1
trg=$2
output_prefix=$3
dataset=$4

cp "${dataset}.${src}.gz" "${output_prefix}.${src}.gz"
cp "${dataset}.${trg}.gz" "${output_prefix}.${trg}.gz"


echo "###### Done: Copying custom corpus"
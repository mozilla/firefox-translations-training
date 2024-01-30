#!/bin/bash
##
# Use local monolingual dataset that is already downloaded to a local disk
# Local path prefix without `.<lang_code>.gz` should be specified as a "dataset" parameter
#

set -x
set -euo pipefail

echo "###### Copying local monolingual dataset"

lang=$1
output_prefix=$2
dataset=$3

mkdir -p "$(dirname "$output_prefix")"
cp "${dataset}.${lang}.gz" "${output_prefix}.gz"


echo "###### Done: Copying local monolingual dataset"

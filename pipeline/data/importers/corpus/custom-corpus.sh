#!/bin/bash
##
# Use custom dataset that is already downloaded to a local disk
# Local path prefix without `.<lang_code>.gz` should be specified as a "dataset" parameter
#
# Usage:
#   bash custom-corpus.sh source target dir dataset
#

set -x
set -euo pipefail

echo "###### Copying custom corpus"

src=$1
trg=$2
dir=$3
dataset=$4

cp "${dataset}.${src}.gz" "${dir}/"
cp "${dataset}.${trg}.gz" "${dir}/"


echo "###### Done: Copying custom corpus"
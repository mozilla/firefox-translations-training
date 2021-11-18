#!/bin/bash
##
# Downloads corpus using sacrebleu
#

set -x
set -euo pipefail

echo "###### Downloading sacrebleu corpus"

src=$1
trg=$2
output_prefix=$3
dataset=$4

sacrebleu -t "${dataset}" -l "${src}-${trg}" --echo src | pigz > "${output_prefix}.${src}.gz"
sacrebleu -t "${dataset}" -l "${src}-${trg}" --echo ref | pigz > "${output_prefix}.${trg}.gz"

echo "###### Done: Downloading sacrebleu corpus"

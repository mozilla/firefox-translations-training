#!/bin/bash
##
# Downloads corpus using sacrebleu
#
# Usage:
#   bash sacrebleu.sh source target dir dataset
#

set -x
set -euo pipefail

echo "###### Downloading sacrebleu corpus"

src=$1
trg=$2
dir=$3
dataset=$4

source "${WORKDIR}/pipeline/setup/activate-python.sh"

test -s "${dir}/${dataset}.${src}" ||
sacrebleu -t "${dataset}" -l "${src}-${trg}" --echo src | pigz > "${dir}/${dataset}.${src}"

test -s "${dir}/${dataset}.${trg}" ||
sacrebleu -t "${dataset}" -l "${src}-${trg}" --echo src | pigz > "${dir}/${dataset}.${trg}"

echo "###### Done: Downloading sacrebleu corpus"

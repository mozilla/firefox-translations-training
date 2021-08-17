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

name="${dataset//[^A-Za-z0-9_- ]/_}"

test -s "${dir}/${name}.${src}" ||
sacrebleu -t "${dataset}" -l "${src}-${trg}" --echo src > "${dir}/${name}.${src}"

test -s "${dir}/${name}.${trg}" ||
sacrebleu -t "${dataset}" -l "${src}-${trg}" --echo ref > "${dir}/${name}.${trg}"

echo "###### Done: Downloading sacrebleu corpus"

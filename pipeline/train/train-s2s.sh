#!/bin/bash
##
# Train a shallow s2s model.
#

set -x
set -euo pipefail

echo "###### Training s2s model"

dir=$1
corpus=$2
devset=$3
vocab=$4
src=$5
trg=$6
extra_params=( "${@:7}" )

cd "$(dirname "${0}")"

bash "train.sh" \
  "configs/model/s2s.yml" \
  "configs/training/s2s.train.yml" \
  "${src}" \
  "${trg}" \
  "${corpus}" \
  "${devset}" \
  "${dir}" \
  "${vocab}" \
  "${extra_params[@]}"


echo "###### Done: Training s2s model"

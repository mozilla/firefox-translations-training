#!/bin/bash
##
# Train a teacher model.
#

set -x
set -euo pipefail

echo "###### Training a teacher model"

dir=$1
corpus=$2
devset=$3
vocab=$4
extra_params=( "${@:5}" )

test -v SRC
test -v TRG

cd "$(dirname "${0}")"

bash "train.sh" \
  "configs/model/teacher.transformer.yml" \
  "configs/training/teacher.train.yml" \
  "${SRC}" \
  "${TRG}" \
  "${corpus}" \
  "${devset}" \
  "${dir}" \
  "${vocab}" \
  "${extra_params[@]}"

echo "###### Training a teacher model"

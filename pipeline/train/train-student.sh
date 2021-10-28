#!/bin/bash
##
# Train a student model.
#

set -x
set -euo pipefail

echo "###### Training a student model"

dir=$1
corpus=$2
devset=$3
vocab=$4
alignment=$5
extra_params=( "${@:6}" )

test -v SRC
test -v TRG

bash "pipeline/train/train.sh" \
  "pipeline/train/configs/model/student.tiny11.yml" \
  "pipeline/train/configs/training/student.train.yml" \
  "${SRC}" \
  "${TRG}" \
  "${corpus}" \
  "${devset}" \
  "${dir}" \
  "${vocab}" \
  --guided-alignment "${alignment}" \
  "${extra_params[@]}"

echo "###### Done: Training a student model"



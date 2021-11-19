#!/bin/bash
##
# Finetune a student model.
#

set -x
set -euo pipefail

echo "###### Finetuning the student model"

dir=$1
corpus=$2
devset=$3
vocab=$4
alignment=$5
student=$6
extra_params=( "${@:7}" )

test -v SRC
test -v TRG

cd "$(dirname "${0}")"

mkdir -p "${dir}"
cp "${student}" "${dir}/model.npz"

bash "train.sh" \
  "configs/model/student.tiny11.yml" \
  "configs/training/student.finetune.yml" \
  "${SRC}" \
  "${TRG}" \
  "${corpus}" \
  "${devset}" \
  "${dir}" \
  "${vocab}" \
  --guided-alignment "${alignment}" \
  "${extra_params[@]}"

echo "###### Done: Finetuning the student model"



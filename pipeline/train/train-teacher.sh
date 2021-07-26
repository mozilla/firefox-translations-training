#!/bin/bash
##
# Train a teacher model.
#
# Usage:
#   bash train-teacher.sh dir corpus devset
#

set -x
set -euo pipefail

echo "###### Training a teacher model"

dir=$1
corpus=$2
devset=$3

test -v SRC
test -v TRG
test -v WORKDIR

test -s "${dir}/model.npz.best-bleu-detok.npz" ||
bash "${WORKDIR}/pipeline/train/train.sh" \
  "${WORKDIR}/pipeline/train/configs/model/teacher.transformer.yml" \
  "${WORKDIR}/pipeline/train/configs/training/teacher.transformer.train.yml" \
  "${SRC}" \
  "${TRG}" \
  "${corpus}" \
  "${devset}" \
  "${dir}"

echo "###### Training a teacher model"

#!/bin/bash -v
##
# Train a teacher ensemble of models.
#
# Usage:
#   bash train-teacher-ensemble.sh dir corpus devset n
#

set -x
set -euo pipefail

echo "###### Training an ensemble of teacher models"

dir=${1}
corpus=${2}
devset=${3}
n=${4}

# This can be parallelized across multiple machines
for i in $(seq 1 ${n}); do
  test -s "${dir}${i}/model.npz.best-bleu-detok.npz" ||
  bash "${WORKDIR}/pipeline/train/train.sh" \
    "${WORKDIR}/pipeline/train/configs/model/teacher.transformer.yml" \
    "${WORKDIR}/pipeline/train/configs/training/teacher.transformer-ens.train.yml" \
    "${SRC}" \
    "${TRG}" \
    "${corpus}" \
    "${devset}" \
    "${dir}${i}"
done

echo "###### Done: Training an ensemble of teacher models"

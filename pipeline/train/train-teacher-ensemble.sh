#!/bin/bash -v
##
# Train a teacher ensemble of models.
#
# Usage:
#   bash train-teacher-ensemble.sh dir corpus devset n
#

set -x
set -euo pipefail

dir=${1}
corpus=${2}
devset=${3}
n=${4}

#TODO: parallelize across multiple machines

for i in $(seq 1 ${n}); do
  bash "${WORKDIR}/pipeline/train/train.sh" \
    "${WORKDIR}/pipeline/train/configs/model/teacher.transformer.yml" \
    "${WORKDIR}/pipeline/train/configs/training/teacher.transformer-ens.train.yml" \
    "${SRC}" \
    "${TRG}" \
    "${corpus}" \
    "${devset}" \
    "${dir}${i}"
done

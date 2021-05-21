#!/bin/bash -v
##
# Train a teacher ensemble of models.
#
# Usage:
#   bash train-teacher-ensemble.sh n
#

set -x
set -euo pipefail

n=$1

#TODO: parallelize across multiple machines

for i in $(seq 1 $n)
do
  bash ./train.sh \
    ${WORKDIR}/pipeline/train/configs/model/teacher.transformer.yml \
    ${WORKDIR}/pipeline/train/configs/training/teacher.transformer-ens.train.yml \
    $SRC \
    $TRG \
    ${DATA_DIR}/clean/corpus \
    ${DATA_DIR}/original/devset \
    ${MODELS_DIR}/$SRC-$TRG/teacher-ens$i
done
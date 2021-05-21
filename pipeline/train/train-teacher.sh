#!/bin/bash -v
##
# Train a teacher model.
#
# Usage:
#   bash train-teacher.sh
#

set -x
set -euo pipefail

bash ./train.sh \
  ${WORKDIR}/pipeline/train/configs/model/teacher.transformer.yml \
  ${WORKDIR}/pipeline/train/configs/training/teacher.transformer.train.yml \
  $SRC \
  $TRG \
  ${DATA_DIR}/clean/corpus \
  ${DATA_DIR}/original/devset \
  ${MODELS_DIR}/$SRC-$TRG/teacher


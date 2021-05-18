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
  configs/model/teacher.transformer.yml \
  configs/training/teacher.transformer.train.yml \
  $SRC \
  $TRG \
  ${DATA_DIR}/clean/corpus \
  ${DATA_DIR}/original/devset \
  ${MODELS_DIR}/teacher


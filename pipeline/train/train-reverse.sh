#!/bin/bash -v
##
# Train a reverse model.
#
# Usage:
#   bash train-teacher.sh
#

set -x
set -euo pipefail

bash ./train.sh \
  ${WORKDIR}/pipeline/train/configs/model/reverse.s2s.yml \
  ${WORKDIR}/pipeline/train/configs/training/reverse.train.yml \
  $TRG \
  $SRC \
  ${DATA_DIR}/clean/corpus \
  ${DATA_DIR}/original/devset \
  ${MODELS_DIR}/reverse


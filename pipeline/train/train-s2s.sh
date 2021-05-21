#!/bin/bash -v
##
# Train a shallow s2s model.
#
# Usage:
#   bash train-teacher.sh [src] [trg]
#

set -x
set -euo pipefail

src=${1:-SRC}
trg=${2:-TRG}


bash ${WORKDIR}/pipeline/train/train.sh \
  ${WORKDIR}/pipeline/train/configs/model/s2s.yml \
  ${WORKDIR}/pipeline/train/configs/training/s2s.train.yml \
  $src \
  $trg \
  ${DATA_DIR}/clean/corpus \
  ${DATA_DIR}/original/devset \
  ${MODELS_DIR}/$src-$trg/s2s


#!/bin/bash -v
##
# Train a student model.
#
# Usage:
#   bash train-student.sh
#

set -x
set -euo pipefail

bash ${WORKDIR}/pipeline/train/train.sh \
  ${WORKDIR}/pipeline/train/configs/model/student.tiny11.yml \
  ${WORKDIR}/pipeline/train/configs/training/student.train.yml \
  $SRC \
  $TRG \
  ${DATA_DIR}/filtered/corpus \
  ${DATA_DIR}/original/devset \
  ${MODELS_DIR}/$SRC-$TRG/student \
  --guided-alignment ${DATA_DIR}/alignment/corpus.aln.gz



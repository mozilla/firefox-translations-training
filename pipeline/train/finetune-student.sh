#!/bin/bash -v
##
# Finetune a student model.
#
# Usage:
#   bash train-student.sh
#

set -x
set -euo pipefail

bash ./train.sh \
  ${WORKDIR}/pipeline/train/configs/model/student.tiny11.yml \
  ${WORKDIR}/pipeline/train/configs/training/student.finetune.yml \
  $SRC \
  $TRG \
  ${DATA_DIR}/augmented/corpus \
  ${DATA_DIR}/original/devset \
  ${MODELS_DIR}/student \
  --guided-alignment ${DATA_DIR}/alignment/corpus.aln.gz



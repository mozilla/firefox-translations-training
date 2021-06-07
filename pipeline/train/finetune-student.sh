#!/bin/bash -v
##
# Finetune a student model.
#
# Usage:
#   bash finetune-student.sh
#

set -x
set -euo pipefail

mkdir -p ${MODELS_DIR}/$SRC-$TRG/student-finetuned
cp ${MODELS_DIR}/$SRC-$TRG/student/model.npz.best-bleu-detok.npz ${MODELS_DIR}/$SRC-$TRG/student-finetuned/model.npz

bash ./train.sh \
  ${WORKDIR}/pipeline/train/configs/model/student.tiny11.yml \
  ${WORKDIR}/pipeline/train/configs/training/student.finetune.yml \
  $SRC \
  $TRG \
  ${DATA_DIR}/filtered/corpus \
  ${DATA_DIR}/original/devset \
  ${MODELS_DIR}/$SRC-$TRG/student-finetuned \
  --guided-alignment ${DATA_DIR}/alignment/corpus.aln.gz



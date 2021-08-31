#!/bin/bash
##
# Finetune a student model.
#
# Usage:
#   bash finetune-student.sh dir corpus devset student alignment
#

set -x
set -euo pipefail

echo "###### Finetuning the student model"

dir=$1
corpus=$2
devset=$3
student=$4
alignment=$5

test -v SRC
test -v TRG

if [ ! -s "${dir}/model.npz.best-bleu-detok.npz" ]; then
  mkdir -p "${dir}"
  cp "${student}/model.npz.best-bleu-detok.npz" "${dir}/model.npz"
  cp "${student}/vocab.spm" "${dir}/"

  bash "pipeline/train/train.sh" \
    "pipeline/train/configs/model/student.tiny11.yml" \
    "pipeline/train/configs/training/student.finetune.yml" \
    "${SRC}" \
    "${TRG}" \
    "${corpus}" \
    "${devset}" \
    "${dir}" \
    --guided-alignment "${alignment}/corpus.aln.gz"
fi

echo "###### Done: Finetuning the student model"



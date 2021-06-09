#!/bin/bash -v
##
# Finetune a student model.
#
# Usage:
#   bash finetune-student.sh dir corpus devset student alignment
#

set -x
set -euo pipefail

dir=${1}
corpus=${2}
devset=${3}
student=${4}
alignment=${5}

test -v SRC
test -v TRG
test -v WORKDIR

mkdir -p "${dir}"
cp ${student}/model.npz.best-bleu-detok.npz "${dir}/model.npz"
cp "${student}/vocab.spm" "${dir}/"

bash "${WORKDIR}/pipeline/train/train.sh" \
  "${WORKDIR}/pipeline/train/configs/model/student.tiny11.yml" \
  "${WORKDIR}/pipeline/train/configs/training/student.finetune.yml" \
  "${SRC}" \
  "${TRG}" \
  "${corpus}" \
  "${devset}" \
  "${dir}" \
  --guided-alignment "${alignment}/corpus.aln.gz"



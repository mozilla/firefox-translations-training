#!/bin/bash
##
# Train a student model.
#
# Usage:
#   bash train-student.sh  dir corpus devset teacher alignment
#

set -x
set -euo pipefail

echo "###### Training a student model"

dir=$1
corpus=$2
devset=$3
teacher=$4
alignment=$5
vocab=$6

test -v SRC
test -v TRG

mkdir -p "${dir}"
# use teacher's vocab, otherwise alignments won't work
cp   "${teacher}/vocab.spm" "${dir}/"

test -s "${dir}/model.npz.best-bleu-detok.npz" ||
bash "pipeline/train/train.sh" \
  "pipeline/train/configs/model/student.tiny11.yml" \
  "pipeline/train/configs/training/student.train.yml" \
  "${SRC}" \
  "${TRG}" \
  "${corpus}" \
  "${devset}" \
  "${dir}" \
  "${vocab}" \
  --guided-alignment "${alignment}/corpus.aln.gz"

echo "###### Done: Training a student model"



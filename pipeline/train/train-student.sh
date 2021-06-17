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

test -v SRC
test -v TRG
test -v WORKDIR

mkdir -p "${dir}"
# use teacher's vocab, otherwise alignments won't work
cp   "${teacher}/vocab.spm" "${dir}/"

bash "${WORKDIR}/pipeline/train/train.sh" \
  "${WORKDIR}/pipeline/train/configs/model/student.tiny11.yml" \
  "${WORKDIR}/pipeline/train/configs/training/student.train.yml" \
  "${SRC}" \
  "${TRG}" \
  "${corpus}" \
  "${devset}" \
  "${dir}" \
  --guided-alignment "${alignment}/corpus.aln.gz"

echo "###### Done: Training a student model"



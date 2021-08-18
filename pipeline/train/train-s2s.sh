#!/bin/bash
##
# Train a shallow s2s model.
#
# Usage:
#   bash train-s2s.sh  dir corpus devset [src] [trg]
#

set -x
set -euo pipefail

echo "###### Training s2s model"

dir=$1
corpus=$2
devset=$3
vocab=$4
src=$5
trg=$6


test -s "${dir}/model.npz.best-bleu-detok.npz" ||
bash "pipeline/train/train.sh" \
  "pipeline/train/configs/model/s2s.yml" \
  "pipeline/train/configs/training/s2s.train.yml" \
  "${src}" \
  "${trg}" \
  "${corpus}" \
  "${devset}" \
  "${dir}" \
  "${vocab}"


echo "###### Done: Training s2s model"

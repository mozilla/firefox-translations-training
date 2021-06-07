#!/bin/bash -v
##
# Train a teacher model.
#
# Usage:
#   bash train-teacher.sh dir corpus devset
#

set -x
set -euo pipefail


dir=$1
corpus=$2
devset=$3


test -v SRC
test -v TRG
test -v WORKDIR

bash ${WORKDIR}/pipeline/train/train.sh \
  ${WORKDIR}/pipeline/train/configs/model/teacher.transformer.yml \
  ${WORKDIR}/pipeline/train/configs/training/teacher.transformer.train.yml \
  $SRC \
  $TRG \
  ${corpus} \
  ${devset} \
  ${dir}


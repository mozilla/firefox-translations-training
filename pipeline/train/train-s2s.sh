#!/bin/bash -v
##
# Train a shallow s2s model.
#
# Usage:
#   bash train-teacher.sh  dir corpus devset [src] [trg]
#

set -x
set -euo pipefail

dir=${1}
corpus=${2}
devset=${3}
src=${4:-${SRC}}
trg=${5:-${TRG}}

test -v WORKDIR

bash "${WORKDIR}/pipeline/train/train.sh" \
  "${WORKDIR}/pipeline/train/configs/model/s2s.yml" \
  "${WORKDIR}/pipeline/train/configs/training/s2s.train.yml" \
  "${src}" \
  "${trg}" \
  "${corpus}" \
  "${devset}" \
  "${dir}"

#!/bin/bash
##
# Continue training a teacher model on a different corpus.
#

set -x
set -euo pipefail

echo "###### Continue training a teacher model"

dir=$1
corpus=$2
devset=$3
vocab=$4
extra_params=( "${@:5}" )

test -v SRC
test -v TRG

cd "$(dirname "${0}")"

bash "train-teacher.sh" \
  "${dir}" \
  "${corpus}" \
  "${devset}" \
  "${vocab}" \
  --no-restore-corpus true \
  "${extra_params[@]}"

echo "###### Done: Continue training a teacher model"

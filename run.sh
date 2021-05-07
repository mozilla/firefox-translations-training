#!/bin/bash
# Runs the whole pipeline end to end
#

set -x
set -euo pipefail


set -a
. ./config.sh
set +a

. ./pipeline/0-setup/install.sh

original=${DATA_DIR}/original
. ./pipeline/1-data/download.sh $original


clean=${DATA_DIR}/clean
. ./pipeline/2-clean/clean-corpus.sh ${original}/corpus ${clean}/corpus

if [-e ${DATA_DIR}/original/mono.en.gz ]; then
  . ./pipeline/2-clean/clean-mono.sh ${original}/mono ${clean}/mono
fi
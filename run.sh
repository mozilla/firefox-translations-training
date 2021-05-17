#!/bin/bash
# Runs the whole pipeline end to end
#

set -x
set -euo pipefail

#.
#├ data
#│   ├ original
#│   │   ├ corpus.ru.gz
#│   │   ├ corpus.en.gz
#│   │   ├ mono.ru.gz
#│   │   ├ mono.en.gz
#│   │   ├ devset.ru.gz
#│   │   └ devset.en.gz
#│   ├ clean
#├ models
#│   ├ teacher
#│   ├ student
#│   ├ reverse


set -a
. ./config.sh
set +a

. ./pipeline/setup/install.sh

PATH="/root/miniconda3/bin:${PATH}"
source /root/miniconda3/etc/profile.d/conda.sh
conda activate bergamot-training-env

original=${DATA_DIR}/original
. ./pipeline/data/download-corpus.sh ${original}/corpus $TRAIN_DATASETS
. ./pipeline/data/download-corpus.sh ${original}/devset $DEVTEST_DATASETS
if [[ ${MONO_DATASETS} ]]; then
  . ./pipeline/data/download-mono.sh ${SRC} $MONO_MAX_SENTENCES ${original}/mono $MONO_DATASETS
fi

clean=${DATA_DIR}/clean
. ./pipeline/clean/clean-corpus.sh ${original}/corpus ${clean}/corpus
if [[ -e ${DATA_DIR}/original/mono.${SRC}.gz ]]; then
  . ./pipeline/clean/clean-mono.sh ${SRC} ${original}/mono ${clean}/mono
fi

. ./pipeline/train/train.sh
. ./pipeline/train/eval.sh
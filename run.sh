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
#│   ├ run-me.sh
#│   └ vocab.spm
#├ models
#│   ├ teacher
#│   ├ student


set -a
. ./config.sh
set +a

. ./pipeline/0-setup/install.sh

export PATH="/root/miniconda3/bin:${PATH}"
source /root/miniconda3/etc/profile.d/conda.sh
conda activate bergamot-training-env

original=${DATA_DIR}/original
. ./pipeline/1-data/download-corpus.sh ${original}/corpus $TRAIN_DATASETS
. ./pipeline/1-data/download-corpus.sh ${original}/devset $DEVTEST_DATASETS
if [! -z "${MONO_DATASETS}" ]; then
  . ./pipeline/1-data/download-mono.sh ${SRC} $MONO_MAX_SENTENCES ${original}/mono $MONO_DATASETS
fi

clean=${DATA_DIR}/clean
. ./pipeline/2-clean/clean-corpus.sh ${original}/corpus ${clean}/corpus
if [-e ${DATA_DIR}/original/mono.en.gz ]; then
  . ./pipeline/2-clean/clean-mono.sh en ${original}/mono ${clean}/mono
fi

. ./pipeline/3-train-teacher/train.sh
. ./pipeline/3-train-teacher/eval.sh
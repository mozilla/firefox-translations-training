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
#│   │   ├ corpus.ru.gz
#│   │   ├ corpus.en.gz
#│   │   ├ mono.ru.gz
#│   │   ├ mono.en.gz
#│   ├ augmented
#│   │   ├ corpus.ru.gz
#│   │   ├ corpus.en.gz
#│   ├ alignment
#│   │   ├ corpus.aln.gz
#├ models
#│   ├ ru-en
#│   │   ├ teacher
#│   │   ├ student
#│   ├ en-ru
#│   │   ├ s2s



set -a
. ./config.sh
set +a

. ./pipeline/setup/install-all.sh

PATH="/root/miniconda3/bin:${PATH}"
source /root/miniconda3/etc/profile.d/conda.sh
conda activate bergamot-training-env

original=${DATA_DIR}/original
. ./pipeline/data/download-corpus.sh ${original}/corpus $TRAIN_DATASETS
. ./pipeline/data/download-corpus.sh ${original}/devset $DEVTEST_DATASETS
if [[ ${MONO_DATASETS_SRC} ]]; then
  . ./pipeline/data/download-mono.sh ${SRC} $MONO_MAX_SENTENCES_SRC ${original}/mono $MONO_DATASETS_SRC
fi
if [[ ${MONO_DATASETS_TRG} ]]; then
  . ./pipeline/data/download-mono.sh ${TRG} $MONO_MAX_SENTENCES_TRG ${original}/mono $MONO_DATASETS_TRG
fi

clean=${DATA_DIR}/clean
. ./pipeline/clean/clean-corpus.sh ${original}/corpus ${clean}/corpus
if [[ -e ${DATA_DIR}/original/mono.${SRC}.gz ]]; then
  . ./pipeline/clean/clean-mono.sh ${SRC} ${original}/mono ${clean}/mono
fi
if [[ -e ${DATA_DIR}/original/mono.${TRG}.gz ]]; then
  . ./pipeline/clean/clean-mono.sh ${TRG} ${original}/mono ${clean}/mono
fi

. ./pipeline/train/train-s2s.sh $TRG $SRC
. ./pipeline/train/eval.sh ${MODELS_DIR}/teacher-ens $TRG $SRC

# TODO: backtranslate and augment corpus


. ./pipeline/train/train-teacher-ens.sh
. ./pipeline/train/eval.sh ${MODELS_DIR}/teacher-ens
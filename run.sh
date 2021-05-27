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
#│   ├ translated
#│   │   ├ mono.ru.gz
#│   │   ├ mono.en.gz
#│   ├ augmented
#│   │   ├ corpus.ru.gz
#│   │   ├ corpus.en.gz
#│   ├ alignment
#│   │   ├ corpus.aln.gz
#│   ├ final
#│   │   ├ corpus.ru.gz
#│   │   ├ corpus.en.gz
#├ models
#│   ├ ru-en
#│   │   ├ teacher
#│   │   ├ student
#│   ├ en-ru
#│   │   ├ s2s


# read config

set -a
. ./config.sh
set +a


# setup

# . ./pipeline/setup/install-all.sh

PATH="/root/miniconda3/bin:${PATH}"
source /root/miniconda3/etc/profile.d/conda.sh
conda activate bergamot-training-env


# download data

original=${DATA_DIR}/original
# . ./pipeline/data/download-corpus.sh ${original}/corpus $TRAIN_DATASETS
# . ./pipeline/data/download-corpus.sh ${original}/devset $DEVTEST_DATASETS
if [[ ${MONO_DATASETS_SRC} ]]; then
 . ./pipeline/data/download-mono.sh ${SRC} $MONO_MAX_SENTENCES_SRC ${original}/mono $MONO_DATASETS_SRC
fi
# if [[ ${MONO_DATASETS_TRG} ]]; then
#  . ./pipeline/data/download-mono.sh ${TRG} $MONO_MAX_SENTENCES_TRG ${original}/mono $MONO_DATASETS_TRG
# fi


# clean data

clean=${DATA_DIR}/clean
# . ./pipeline/clean/clean-corpus.sh ${original}/corpus ${clean}/corpus
if [[ -e ${DATA_DIR}/original/mono.${SRC}.gz ]]; then
 . ./pipeline/clean/clean-mono.sh ${SRC} ${original}/mono ${clean}/mono
fi
# if [[ -e ${original}/mono.${TRG}.gz ]]; then
#  . ./pipeline/clean/clean-mono.sh ${TRG} ${original}/mono ${clean}/mono
# fi


# train backward model

# . ./pipeline/train/train-s2s.sh $TRG $SRC
# . ./pipeline/train/eval.sh ${MODELS_DIR}/$TRG-$SRC/s2s $TRG $SRC


# augment corpus with back translations

# . ./pipeline/translate/translate-mono.sh ${clean}/mono.$TRG.gz ${MODELS_DIR}/$TRG-$SRC/s2s ${DATA_DIR}/translated/mono.$SRC.gz

# augmented=${DATA_DIR}/augmented
# mkdir -p $augmented
# test -s $augmented/corpus.$SRC.gz || cat ${DATA_DIR}/translated/mono.$SRC.gz ${DATA_DIR}/clean/corpus.$SRC.gz > $augmented/corpus.$SRC.gz
# test -s $augmented/corpus.$TRG.gz || cat ${clean}/mono.$TRG.gz ${DATA_DIR}/clean/corpus.$TRG.gz > $augmented/corpus.$TRG.gz
# pigz -dc $augmented/corpus.$SRC.gz | wc -l
# pigz -dc $augmented/corpus.$TRG.gz | wc -l

# train teacher

teacher_dir=${MODELS_DIR}/$SRC-$TRG/teacher
# . ./pipeline/train/train-teacher.sh
# . ./pipeline/train/eval.sh $teacher_dir


# translate with teacher


# . ./pipeline/translate/translate-corpus.sh ${clean}/corpus.$SRC.gz ${clean}/corpus.$TRG.gz $teacher_dir ${DATA_DIR}/translated/corpus.$TRG.gz
. ./pipeline/translate/translate-mono.sh ${clean}/mono.$SRC.gz $teacher_dir ${DATA_DIR}/translated/mono.$TRG.gz

final=${DATA_DIR}/final
mkdir -p $final
test -s $final/corpus.$SRC.gz || cat ${clean}/corpus.$SRC.gz ${clean}/mono.$SRC.gz > $final/corpus.$SRC.gz
test -s $final/corpus.$TRG.gz || cat ${DATA_DIR}/translated/mono.$TRG.gz ${DATA_DIR}/translated/corpus.$TRG.gz > $final/corpus.$TRG.gz
pigz -dc $final/corpus.$SRC.gz | wc -l
pigz -dc $final/corpus.$TRG.gz | wc -l


# ce-filter

# TODO

# train word alignment and lexical shortlists

align_dir=${DATA_DIR}/alignment
. ./pipeline/alignment/generate-alignment-and-shortlist.sh ${final}/corpus ${teacher_dir}/vocab.spm $align_dir

# train student
student_dir=${MODELS_DIR}/$SRC-$TRG/student
# . ./pipeline/train/train-student.sh
# . ./pipeline/train/eval.sh $student_dir


# finetune student

# . ./pipeline/train/finetune-student.sh
# . ./pipeline/train/eval.sh $student_dir



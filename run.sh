#!/bin/bash
# Runs the whole pipeline end to end
#

set -x
set -euo pipefail

#ru-en
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
#│   │   ├ lex.s2t.pruned.gz
#│   ├ merged
#│   │   ├ corpus.ru.gz
#│   │   ├ corpus.en.gz
#│   ├ filtered
#│   │   ├ corpus.ru.gz
#│   │   ├ corpus.en.gz
#├ models
#│   ├ ru-en
#│   │   ├ teacher
#│   │   ├ student
#│   │   ├ student-finetuned
#│   │   ├ speed
#│   ├ en-ru
#│   │   ├ s2s

# read config
set -a
. ./config.sh
set +a

## setup
. ./pipeline/setup/install-all.sh
PATH="/root/miniconda3/bin:${PATH}"
source /root/miniconda3/etc/profile.d/conda.sh
conda activate bergamot-training-env

# set common variables
# data
original=${DATA_DIR}/original
clean=${DATA_DIR}/clean
augmented=${DATA_DIR}/augmented
merged=${DATA_DIR}/merged
filtered=${DATA_DIR}/filtered
align_dir=${DATA_DIR}/alignment
# models
student_dir=${MODELS_DIR}/$SRC-$TRG/student
student_finetuned_dir=${MODELS_DIR}/$SRC-$TRG/student-finetuned
teacher_dir=${MODELS_DIR}/$SRC-$TRG/teacher
s2s=${MODELS_DIR}/$TRG-$SRC/s2s
speed=${MODELS_DIR}/$SRC-$TRG/speed

# download data
. ./pipeline/data/download-corpus.sh ${original}/corpus $TRAIN_DATASETS
. ./pipeline/data/download-corpus.sh ${original}/devset $DEVTEST_DATASETS
test -n "${MONO_DATASETS_SRC}" ||
  . ./pipeline/data/download-mono.sh ${SRC} $MONO_MAX_SENTENCES_SRC ${original}/mono $MONO_DATASETS_SRC
test -n "${MONO_DATASETS_TRG}" ||
  . ./pipeline/data/download-mono.sh ${TRG} $MONO_MAX_SENTENCES_TRG ${original}/mono $MONO_DATASETS_TRG

# clean data
. ./pipeline/clean/clean-corpus.sh ${original}/corpus ${clean}/corpus
test -e ${DATA_DIR}/original/mono.${SRC}.gz ||
  . ./pipeline/clean/clean-mono.sh ${SRC} ${original}/mono ${clean}/mono
test -e ${original}/mono.${TRG}.gz ||
  . ./pipeline/clean/clean-mono.sh ${TRG} ${original}/mono ${clean}/mono

# train backward model
. ./pipeline/train/train-s2s.sh ${s2s} ${clean}/corpus ${original}/devset $TRG $SRC
. ./pipeline/train/eval.sh ${s2s} $TRG $SRC

# augment corpus with back translations
. ./pipeline/translate/translate-mono.sh ${clean}/mono.$TRG.gz ${s2s} ${DATA_DIR}/translated/mono.$SRC.gz
. ./pipeline/utils/merge-corpus.sh ${DATA_DIR}/translated/mono.$SRC.gz \
  ${DATA_DIR}/clean/corpus.$SRC.gz \
  ${clean}/mono.$TRG.gz \
  ${DATA_DIR}/clean/corpus.$TRG.gz \
  $augmented/corpus.$SRC.gz \
  $augmented/corpus.$TRG.gz

# train teacher
. ./pipeline/train/train-teacher.sh "${teacher_dir}" ${clean}/corpus ${original}/devset
. ./pipeline/train/eval.sh "${teacher_dir}"

# translate with teacher
. ./pipeline/translate/translate-corpus.sh "${clean}/corpus.${SRC}.gz" \
  ${clean}/corpus.$TRG.gz \
  $teacher_dir ${DATA_DIR}/translated/corpus.$TRG.gz

. ./pipeline/translate/translate-mono.sh ${clean}/mono.$SRC.gz \
  $teacher_dir \
  ${DATA_DIR}/translated/mono.$TRG.gz

. ./pipeline/utils/merge-corpus.sh ${clean}/corpus.$SRC.gz \
  ${clean}/mono.$SRC.gz \
  ${DATA_DIR}/translated/corpus.$TRG.gz \
  ${DATA_DIR}/translated/mono.$TRG.gz \
  $merged/corpus.$SRC.gz \
  $merged/corpus.$TRG.gz

# cross entropy filtering
. ./pipeline/clean/ce-filter.sh $s2s ${merged}/corpus ${filtered}/corpus

# train word alignment and lexical shortlists
. ./pipeline/alignment/generate-alignment-and-shortlist.sh ${filtered}/corpus ${teacher_dir}/vocab.spm $align_dir

# train student
. ./pipeline/train/train-student.sh \
  $student_dir \
  ${filtered}/corpus \
  ${original}/devset \
  $teacher_dir \
  $align_dir
. ./pipeline/train/eval.sh $student_dir

# finetune student
. ./pipeline/train/finetune-student.sh \
  $student_finetuned_dir \
  ${filtered}/corpus \
  ${original}/devset \
  $student_dir \
  $align_dir
. ./pipeline/train/eval.sh $student_finetuned_dir

# quantize
. ./pipeline/quantize/quantize.sh "${student_finetuned_dir}" "${speed}"

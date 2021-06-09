#!/bin/bash
##
# Runs the whole pipeline end to end
#
# Usage:
#   Run from the current directory
#   bash run.sh
#

set -x
set -euo pipefail

# Directories structure
#
#├ data
#│   └ ru-en
#│      ├ original
#│      │   ├ corpus.ru.gz
#│      │   ├ corpus.en.gz
#│      │   ├ mono.ru.gz
#│      │   ├ mono.en.gz
#│      │   ├ devset.ru.gz
#│      │   └ devset.en.gz
#│      ├ clean
#│      │   ├ corpus.ru.gz
#│      │   ├ corpus.en.gz
#│      │   ├ mono.ru.gz
#│      │   └ mono.en.gz
#│      ├ translated
#│      │   ├ mono.ru.gz
#│      │   └ mono.en.gz
#│      ├ augmented
#│      │   ├ corpus.ru.gz
#│      │   └ corpus.en.gz
#│      ├ alignment
#│      │   ├ corpus.aln.gz
#│      │   └ lex.s2t.pruned.gz
#│      ├ merged
#│      │   ├ corpus.ru.gz
#│      │   └ corpus.en.gz
#│      └ filtered
#│          ├ corpus.ru.gz
#│          └ corpus.en.gz
#├ model
#│   ├ ru-en
#│   │   ├ teacher
#│   │   ├ student
#│   │   ├ student-finetuned
#│   │   ├ speed
#│   │   └ exported
#│   ├ en-ru
#│   │   └ s2s

echo "###### read config "
set -a
. ./config.sh
set +a

echo "######  setup"
. ./pipeline/setup/install-all.sh
PATH="/root/miniconda3/bin:${PATH}"
source /root/miniconda3/etc/profile.d/conda.sh
conda activate bergamot-training-env

echo "######  set common variables"
# data
original="${DATA_DIR}/${SRC}-${TRG}/original"
clean="${DATA_DIR}/${SRC}-${TRG}/clean"
augmented="${DATA_DIR}/${SRC}-${TRG}/augmented"
translated="${DATA_DIR}/${SRC}-${TRG}/translated"
merged="${DATA_DIR}/${SRC}-${TRG}/merged"
filtered="${DATA_DIR}/${SRC}-${TRG}/filtered"
align_dir="${DATA_DIR}/${SRC}-${TRG}/alignment"
# models
student_dir="${MODELS_DIR}/${SRC}-${TRG}/student"
student_finetuned_dir="${MODELS_DIR}/${SRC}-${TRG}/student-finetuned"
teacher_dir="${MODELS_DIR}/${SRC}-${TRG}/teacher"
s2s="${MODELS_DIR}/${TRG}-${SRC}/s2s"
speed="${MODELS_DIR}/${SRC}-${TRG}/speed"
exported="${MODELS_DIR}/${SRC}-${TRG}/exported"

echo "######  download data"
. ./pipeline/data/download-corpus.sh "${original}/corpus" "${TRAIN_DATASETS}"
. ./pipeline/data/download-corpus.sh "${original}/devset" "${DEVTEST_DATASETS}"
test -n "${MONO_DATASETS_SRC}" ||
  . ./pipeline/data/download-mono.sh "${SRC}" "${MONO_MAX_SENTENCES_SRC}" "${original}/mono" "${MONO_DATASETS_SRC}"
test -n "${MONO_DATASETS_TRG}" ||
  . ./pipeline/data/download-mono.sh "${TRG}" "${MONO_MAX_SENTENCES_TRG}" "${original}/mono" "${MONO_DATASETS_TRG}"

echo "######  clean data"
. ./pipeline/clean/clean-corpus.sh "${original}/corpus" "${clean}/corpus"
test -e "${original}/mono.${SRC}.gz" ||
  . ./pipeline/clean/clean-mono.sh "${SRC}" "${original}/mono" "${clean}/mono"
test -e "${original}/mono.${TRG}.gz" ||
  . ./pipeline/clean/clean-mono.sh "${TRG}" "${original}/mono" "${clean}/mono"

echo "######  train backward model"
. ./pipeline/train/train-s2s.sh "${s2s}" "${clean}/corpus" "${original}/devset" "${TRG}" "${SRC}"
. ./pipeline/train/eval.sh "${s2s}" "${TRG}" "${SRC}"

echo "######  augment corpus with back translations"
. ./pipeline/translate/translate-mono.sh "${clean}/mono.${TRG}.gz" "${s2s}" "${translated}/mono.${SRC}.gz"
. ./pipeline/utils/merge-corpus.sh \
  "${translated}/mono.${SRC}.gz" \
  "${clean}/corpus.${SRC}.gz" \
  "${clean}/mono.${TRG}.gz" \
  "${clean}/corpus.${TRG}.gz" \
  "${augmented}/corpus.${SRC}.gz" \
  "${augmented}/corpus.${TRG}.gz"

echo "######  train teacher"
. ./pipeline/train/train-teacher.sh "${teacher_dir}" "${clean}/corpus" "${original}/devset"
. ./pipeline/train/eval.sh "${teacher_dir}"

echo "######  translate with teacher"
. ./pipeline/translate/translate-corpus.sh "${clean}/corpus.${SRC}.gz" \
  "${clean}/corpus.${TRG}.gz" \
  "${teacher_dir}" "${translated}/corpus.${TRG}.gz"

. ./pipeline/translate/translate-mono.sh "${clean}/mono.${SRC}.gz" \
  "${teacher_dir}" \
  "${translated}/mono.${TRG}.gz"

. ./pipeline/utils/merge-corpus.sh "${clean}/corpus.${SRC}.gz" \
  "${clean}/mono.${SRC}.gz" \
  "${translated}/corpus.${TRG}.gz" \
  "${translated}/mono.${TRG}.gz" \
  "${merged}/corpus.${SRC}.gz" \
  "${merged}/corpus.${TRG}.gz"

echo "######  cross entropy filtering"
. ./pipeline/clean/ce-filter.sh "${s2s}" "${merged}/corpus" "${filtered}/corpus"

echo "######  train word alignment and lexical shortlists"
. ./pipeline/alignment/generate-alignment-and-shortlist.sh "${filtered}/corpus" \
  "${teacher_dir}/vocab.spm" "${align_dir}"

echo "######  train student"
. ./pipeline/train/train-student.sh \
  "${student_dir}" \
  "${filtered}/corpus" \
  "${original}/devset" \
  "${teacher_dir}" \
  "${align_dir}"
. ./pipeline/train/eval.sh "${student_dir}"

echo "######  finetune student"
. ./pipeline/train/finetune-student.sh \
  "${student_finetuned_dir}" \
  "${filtered}/corpus" \
  "${original}/devset" \
  "${student_dir}" \
  "${align_dir}"
. ./pipeline/train/eval.sh "${student_finetuned_dir}"

echo "######   quantize"
. ./pipeline/quantize/quantize.sh \
  "${student_finetuned_dir}" \
  "${align_dir}/lex.s2t.pruned.gz" \
  "${original}/devset.${SRC}.gz" \
  "${speed}"
. ./pipeline/quantize/eval.sh "${speed}" "${align_dir}/lex.s2t.pruned.gz"

echo "######  export"
. ./pipeline/quantize/export.sh "${speed}" "${align_dir}/lex.s2t.pruned.gz" "${exported}"

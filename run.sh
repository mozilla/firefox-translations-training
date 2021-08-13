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
#│   ├ cache
#│   │  ├ corpus
#│   │  │  └ opus
#│   │  │    ├ ada83_v1.en.gz
#│   │  │    └ ada83_v1.ru.gz
#│   │  └ mono
#│   │     └ news-crawl
#│   │       ├ news.2019.ru.gz
#│   │       └ news.2019.en.gz
#│   └ ru-en
#│      └ test
#│        ├ original
#│        │   ├ corpus.ru.gz
#│        │   ├ corpus.en.gz
#│        │   ├ mono.ru.gz
#│        │   ├ mono.en.gz
#│        │   ├ devset.ru.gz
#│        │   └ devset.en.gz
#│        ├ evaluation
#│        │   ├ wmt12.ru
#│        │   ├ wmt12.en
#│        │   ├ wmt20.ru
#│        │   ├ wmt20.en
#│        ├ clean
#│        │   ├ corpus.ru.gz
#│        │   ├ corpus.en.gz
#│        │   ├ mono.ru.gz
#│        │   └ mono.en.gz
#│        ├ biclean
#│        │   ├ corpus.ru.gz
#│        │   ├ corpus.en.gz
#│        ├ translated
#│        │   ├ mono.ru.gz
#│        │   └ mono.en.gz
#│        ├ augmented
#│        │   ├ corpus.ru.gz
#│        │   └ corpus.en.gz
#│        ├ alignment
#│        │   ├ corpus.aln.gz
#│        │   └ lex.s2t.pruned.gz
#│        ├ merged
#│        │   ├ corpus.ru.gz
#│        │   └ corpus.en.gz
#│        └ filtered
#│            ├ corpus.ru.gz
#│            └ corpus.en.gz
#├ model
#│   ├ ru-en
#│   │   └ test
#│   │      ├ teacher
#│   │      ├ student
#│   │      ├ student-finetuned
#│   │      ├ speed
#│   │      └ exported
#│   ├ en-ru
#│      └ test
#│         └ s2s
#│
#├ experiments
#│   └ ru-en
#│      └ test
#│         └ config.sh

echo "###### read config "
source ./config.sh

echo "######  set common variables"
# data
data_dir="${DATA_ROOT_DIR}/data/${SRC}-${TRG}/${EXPERIMENT}"
cache_dir="${DATA_ROOT_DIR}/cache"
original="${data_dir}/original"
evaluation="${data_dir}/evaluation"
clean="${data_dir}/clean"
biclean="${data_dir}/biclean"
augmented="${data_dir}/augmented"
translated="${data_dir}/translated"
merged="${data_dir}/merged"
filtered="${data_dir}/filtered"
align_dir="${data_dir}/alignment"
# models
models_dir="${DATA_ROOT_DIR}/models/${SRC}-${TRG}/${EXPERIMENT}"
student_dir="${models_dir}/student"
student_finetuned_dir="${models_dir}/student-finetuned"
teacher_dir="${models_dir}/teacher"
s2s="${DATA_ROOT_DIR}/models/${TRG}-${SRC}/${EXPERIMENT}/s2s"
speed="${models_dir}/speed"
exported="${models_dir}/exported"

echo "###### save experiment "
experiment_dir="${EXPERIMENTS_DIR}/${SRC}-${TRG}/${EXPERIMENT}"
mkdir -p "${experiment_dir}"
cp ./config.sh "${experiment_dir}/config.sh"
cp -r ./pipeline/translate/configs "${experiment_dir}/"

echo "######  setup"
bash ./pipeline/setup/install-all.sh

echo "######  download data"
# shellcheck disable=SC2086
bash ./pipeline/data/download-corpus.sh "${original}/corpus" "${cache_dir}" ${TRAIN_DATASETS}
# shellcheck disable=SC2086
bash ./pipeline/data/download-corpus.sh "${original}/devset" "${cache_dir}" ${DEVTEST_DATASETS}
# shellcheck disable=SC2086
bash ./pipeline/data/download-eval.sh "${evaluation}" "${cache_dir}" ${TEST_DATASETS}
# shellcheck disable=SC2086
test -n "${MONO_DATASETS_SRC}" &&
  bash ./pipeline/data/download-mono.sh "${SRC}" "${MONO_MAX_SENTENCES_SRC}" "${original}/mono" "${cache_dir}" ${MONO_DATASETS_SRC}
# shellcheck disable=SC2086
test -n "${MONO_DATASETS_TRG}" &&
  bash ./pipeline/data/download-mono.sh "${TRG}" "${MONO_MAX_SENTENCES_TRG}" "${original}/mono" "${cache_dir}" ${MONO_DATASETS_TRG}

echo "######  clean data"
bash ./pipeline/clean/clean-corpus.sh "${original}/corpus" "${clean}/corpus"
bash ./pipeline/clean/bicleaner.sh "${clean}/corpus" "${biclean}/corpus"
test -e "${original}/mono.${SRC}.gz" &&
  bash ./pipeline/clean/clean-mono.sh "${SRC}" "${original}/mono" "${clean}/mono"
test -e "${original}/mono.${TRG}.gz" &&
  bash ./pipeline/clean/clean-mono.sh "${TRG}" "${original}/mono" "${clean}/mono"

echo "######  train backward model"
bash ./pipeline/train/train-s2s.sh "${s2s}" "${biclean}/corpus" "${original}/devset" "${TRG}" "${SRC}"
bash ./pipeline/train/eval.sh "${s2s}" "${evaluation}" "${TRG}" "${SRC}"

if [ -e "${clean}/mono.${TRG}.gz" ]; then
  echo "######  augment corpus with back translations"
  bash ./pipeline/translate/translate-mono.sh "${clean}/mono.${TRG}.gz" "${s2s}" "${translated}/mono.${SRC}.gz"
  bash ./pipeline/utils/merge-corpus.sh \
    "${translated}/mono.${SRC}.gz" \
    "${biclean}/corpus.${SRC}.gz" \
    "${clean}/mono.${TRG}.gz" \
    "${biclean}/corpus.${TRG}.gz" \
    "${augmented}/corpus.${SRC}.gz" \
    "${augmented}/corpus.${TRG}.gz"
  teacher_corpus="${augmented}/corpus"
else
  echo "###### skipping augmentation"
  teacher_corpus="${biclean}/corpus"
fi

echo "######  train teacher"
bash ./pipeline/train/train-teacher.sh "${teacher_dir}" "${teacher_corpus}" "${original}/devset"

echo "######  evaluate teacher"
bash ./pipeline/train/eval.sh "${teacher_dir}" "${evaluation}"

echo "######  translate with teacher"
bash ./pipeline/translate/translate-corpus.sh "${clean}/corpus.${SRC}.gz" \
  "${clean}/corpus.${TRG}.gz" \
  "${teacher_dir}" "${translated}/corpus.${TRG}.gz"

bash ./pipeline/translate/translate-mono.sh "${clean}/mono.${SRC}.gz" \
  "${teacher_dir}" \
  "${translated}/mono.${TRG}.gz"

bash ./pipeline/utils/merge-corpus.sh "${clean}/corpus.${SRC}.gz" \
  "${clean}/mono.${SRC}.gz" \
  "${translated}/corpus.${TRG}.gz" \
  "${translated}/mono.${TRG}.gz" \
  "${merged}/corpus.${SRC}.gz" \
  "${merged}/corpus.${TRG}.gz"

echo "######  cross entropy filtering"
bash ./pipeline/clean/ce-filter.sh "${s2s}" "${merged}/corpus" "${filtered}/corpus"

echo "######  train word alignment and lexical shortlists"
bash ./pipeline/alignment/generate-alignment-and-shortlist.sh "${filtered}/corpus" \
  "${teacher_dir}/vocab.spm" "${align_dir}"

echo "######  train student"
bash ./pipeline/train/train-student.sh \
  "${student_dir}" \
  "${filtered}/corpus" \
  "${original}/devset" \
  "${teacher_dir}" \
  "${align_dir}"
bash ./pipeline/train/eval.sh "${student_dir}" "${evaluation}"

echo "######  finetune student"
bash ./pipeline/train/finetune-student.sh \
  "${student_finetuned_dir}" \
  "${filtered}/corpus" \
  "${original}/devset" \
  "${student_dir}" \
  "${align_dir}"
bash ./pipeline/train/eval.sh "${student_finetuned_dir}" "${evaluation}"

echo "######   quantize"
bash ./pipeline/quantize/quantize.sh \
  "${student_finetuned_dir}" \
  "${align_dir}/lex.s2t.pruned.gz" \
  "${original}/devset.${SRC}.gz" \
  "${speed}"
bash ./pipeline/quantize/eval.sh "${speed}" "${align_dir}/lex.s2t.pruned.gz" "${evaluation}"

echo "######  export"
bash ./pipeline/quantize/export.sh "${speed}" "${align_dir}/lex.s2t.pruned.gz" "${exported}"

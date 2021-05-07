#!/bin/bash
# Downloads datasets
#
# Usage:
#   bash download.sh output_dir
#

set -x
set -euo pipefail

test -v DATA_DIR
test -v CUDA_DIR
test -v SRC
test -v TRG
test -v TRAIN_DATASETS
test -v DEVTEST_DATASETS

src_iso = $(python -c "from mtdata.iso import iso3_code; print(iso3_code('${SRC}}', fail_error=True))")
trg_iso = $(python -c "from mtdata.iso import iso3_code; print(iso3_code('${TRG}', fail_error=True))")

dir = $@
src_corpus=${dir}/corpus.${SRC}.gz
trg_corpus=${dir}/corpus.${TRG}.gz
src_devset=${dir}/devset.${SRC}.gz
trg_devset=${dir}/devset.${TRG}.gz

mkdir -p $dir

if [ ! -e ${trg_corpus} ]; then
  echo "Downloading training datasets"
  mtdata get -l $SRC-$TRG -tr ${TRAIN_DATASETS} -o ${dir}
  cat ${dir}/train-parts/*.${src_iso} | pigz > $src_corpus
  cat ${dir}/train-parts/*.${trg_iso} | pigz > $trg_corpus
else
  echo "Training dataset already exists"
fi

test -s $src_corpus || exit 1
test -s $trg_corpus || exit 1


if [ ! -e ${dir}/devset.${TRG}.gz ]; then
  echo "Downloading devtest datasets"
  mtdata get -l $SRC-$TRG -tt ${DEVTEST_DATASETS}  -o ${dir}
  cat ${dir}/tests/*.${src_iso} | pigz > $src_devset
  cat ${dir}/tests/*.${trg_iso} | pigz > $trg_devset
else
  echo "Devtest dataset already exists"
fi

test -s $src_devset || exit 1
test -s $trg_devset || exit 1



# TODO: download mono dataset





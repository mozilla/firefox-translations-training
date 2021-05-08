#!/bin/bash
# Downloads datasets
#
# Usage:
#   bash download-corpus.sh output_prefix dataset [dataset...]
#

set -x
set -euo pipefail

test -v SRC
test -v TRG

src_iso = $(python -c "from mtdata.iso import iso3_code; print(iso3_code('${SRC}}', fail_error=True))")
trg_iso = $(python -c "from mtdata.iso import iso3_code; print(iso3_code('${TRG}', fail_error=True))")

prefix=$1
datsets=${@:2}

src_corpus=${prefix}.${SRC}.gz
trg_corpus=${prefix}.${TRG}.gz
dir=$(dirname prefix)

mkdir -p $dir

if [ ! -e ${trg_corpus} ]; then
  echo "Downloading datasets"
  mtdata get -l $SRC-$TRG -tr $datsets -o ${dir}
  cat ${dir}/train-parts/*.${src_iso} | pigz > $src_corpus
  cat ${dir}/train-parts/*.${trg_iso} | pigz > $trg_corpus
else
  echo "Datasets already exists"
fi

test -s $src_corpus || exit 1
test -s $trg_corpus || exit 1

rm -rf ${dir}/train-parts







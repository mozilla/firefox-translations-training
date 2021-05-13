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

prefix=$1
datasets=${@:2}

src_corpus=${prefix}.${SRC}.gz
trg_corpus=${prefix}.${TRG}.gz
dir=$(dirname $prefix)

mkdir -p $dir

if [ ! -e ${trg_corpus} ]; then
  echo "Downloading datasets"
  mkdir -p ${dir}/train-parts

  for dataset in $datasets; do
    echo "Downloading dataset ${dataset}"
    if [[ $dataset == mtdata* ]]; then
      src_iso=$(python -c "from mtdata.iso import iso3_code; print(iso3_code('${SRC}', fail_error=True))")
      trg_iso=$(python -c "from mtdata.iso import iso3_code; print(iso3_code('${TRG}', fail_error=True))")
      mtdata get -l "${SRC}"-"${TRG}" -tr ${dataset#"mtdata_"} -o "${dir}"
      for f in ${dir}/train-parts/*."${src_iso}"; do
          mv "$f" ${dir}/train-parts/${dataset}.$SRC
      done
      for f in ${dir}/train-parts/*."${trg_iso}"; do
          mv "$f" ${dir}/train-parts/${dataset}.$TRG
      done
    elif [[ $dataset == opus_* ]]; then
      opus_path=${dataset#"opus_"}
      dataset_path=${dir}/train-parts/${opus_path%\/*}.txt.zip
      wget -nc -O "$dataset_path"  https://object.pouta.csc.fi/${opus_path}/moses/"${SRC}"-"${TRG}".txt.zip || \
      rm $dataset_path && wget -nc -O "$dataset_path"  https://object.pouta.csc.fi/${opus_path}/moses/"${TRG}"-"${SRC}".txt.zip
      unzip "$dataset_path" -d ${dir}/train-parts/
    elif [[ $dataset == Paracrawl* ]]; then
      echo "Paracrawl unsupported"
      exit 1
    fi
  done

  cat ${dir}/train-parts/*."${SRC}" | pigz > "$src_corpus"
  cat ${dir}/train-parts/*."${TRG}" | pigz > "$trg_corpus"


else
  echo "Datasets already exists"
fi

test -s "$src_corpus" || exit 1
test -s "$trg_corpus" || exit 1

rm -rf "${dir}"/train-parts







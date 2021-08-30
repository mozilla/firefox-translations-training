#!/bin/bash
##
# Downloads a dataset using mtdata
#
# Usage:
#   bash mtdata.sh source target dir dataset
#

set -x
set -euo pipefail

echo "###### Downloading mtdata corpus"

src=$1
trg=$2
dir=$3
dataset=$4

src_iso=$(python -c "from mtdata.iso import iso3_code; print(iso3_code('${src}', fail_error=True))")
trg_iso=$(python -c "from mtdata.iso import iso3_code; print(iso3_code('${trg}', fail_error=True))")

if [ ! -e "${dir}/${dataset}.${trg}" ]; then
  mtdata get -l "${src}-${trg}" -tr "${dataset}" -o "${dir}"

  for f in "${dir}"/train-parts/*."${src_iso}"; do
    mv "${f}" "${dir}/${dataset}.${src}"
  done
  for f in "${dir}"/train-parts/*."${trg_iso}"; do
    mv "${f}" "${dir}/${dataset}.${trg}"
  done

  rm -rf "${dir}/train-parts"
fi


echo "###### Done: Downloading mtdata corpus"

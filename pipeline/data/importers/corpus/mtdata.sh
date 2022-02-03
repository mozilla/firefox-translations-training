#!/bin/bash
##
# Downloads a dataset using mtdata
#

set -x
set -euo pipefail

echo "###### Downloading mtdata corpus"

src=$1
trg=$2
output_prefix=$3
dataset=$4

tmp="$(dirname "${output_prefix}")/mtdata/${dataset}"
mkdir -p "${tmp}"

src_iso=$(python -c "from mtdata.iso import iso3_code; print(iso3_code('${src}', fail_error=True))")
trg_iso=$(python -c "from mtdata.iso import iso3_code; print(iso3_code('${trg}', fail_error=True))")

mtdata get -l "${src}-${trg}" -tr "${dataset}" -o "${tmp}" --compress

mv "${tmp}/train-parts/${dataset}.${src_iso}.gz" "${output_prefix}.${src}.gz"
mv "${tmp}/train-parts/${dataset}.${trg_iso}.gz" "${output_prefix}.${trg}.gz"

rm -rf "${tmp}"

echo "###### Done: Downloading mtdata corpus"

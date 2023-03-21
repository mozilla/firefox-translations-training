#!/bin/bash
##
# Downloads flores dataset
# Dataset type can be "dev" or "devtest"
#

set -x
set -euo pipefail

echo "###### Downloading flores corpus"

src=$1
trg=$2
output_prefix=$3
dataset=$4

tmp="$(dirname "${output_prefix}")/flores/${dataset}"
mkdir -p "${tmp}"

wget -O "${tmp}/flores101_dataset.tar.gz" "https://dl.fbaipublicfiles.com/flores101/dataset/flores101_dataset.tar.gz"
tar -xzf "${tmp}/flores101_dataset.tar.gz" -C "${tmp}" --no-same-owner

flores_code() {
  code=$1

  if [ "${code}" == "zh" ] || [ "${code}" == "zh-Hans" ]; then
    flores_code="zho_simpl"
  elif [ "${code}" == "zh-Hant" ]; then
    flores_code="zho_trad"
  elif [ "${code}" == "sw" ]; then
    flores_code="swh"
  else
    flores_code=$(python -c "from mtdata.iso import iso3_code; print(iso3_code('${code}', fail_error=True))")
  fi

  echo "${flores_code}"
}

src_flores=$(flores_code "${src}")
trg_flores=$(flores_code "${trg}")

pigz -c "${tmp}/flores101_dataset/${dataset}/${src_flores}.${dataset}" > "${output_prefix}.${src}.gz"
pigz -c "${tmp}/flores101_dataset/${dataset}/${trg_flores}.${dataset}" > "${output_prefix}.${trg}.gz"

rm -rf "${tmp}"

echo "###### Done: Downloading flores corpus"

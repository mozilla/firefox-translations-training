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
dir=$3
dataset=$4

tmp="${dir}/flores"
mkdir -p "${tmp}"

test -s "${tmp}/flores101_dataset.tar.gz" ||
  wget -O "${tmp}/flores101_dataset.tar.gz" "https://dl.fbaipublicfiles.com/flores101/dataset/flores101_dataset.tar.gz"

tar -xzf "${tmp}/flores101_dataset.tar.gz" -C "${tmp}" --no-same-owner

flores_code() {
  code=$1

  if [ "${code}" == "zh" ] || [ "${code}" == "zh-Hans" ]; then
    flores_code="zho_simpl"
  elif [ "${code}" == "zh-Hant" ]; then
    flores_code="zho_trad"
  else
    flores_code=$(python -c "from mtdata.iso import iso3_code; print(iso3_code('${code}', fail_error=True))")
  fi

  echo "${flores_code}"
}

src_flores=$(flores_code "${src}")
trg_flores=$(flores_code "${trg}")

cp "${tmp}/flores101_dataset/${dataset}/${src_flores}.${dataset}" "${dir}/flores.${src}"
cp "${tmp}/flores101_dataset/${dataset}/${trg_flores}.${dataset}" "${dir}/flores.${trg}"

rm -rf "${tmp}"

echo "###### Done: Downloading flores corpus"

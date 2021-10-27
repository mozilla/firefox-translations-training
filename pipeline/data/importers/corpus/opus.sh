#!/bin/bash
##
# Downloads corpus using opus
#

set -x
set -euo pipefail

echo "###### Downloading opus corpus"

src=$1
trg=$2
dir=$3
dataset=$4

name=${dataset%%/*}

if [ ! -s "${dir}/${name}.${src}-${trg}.${trg}" ] && [ ! -s "${dir}/${name}.${trg}-${src}.${trg}" ]; then
  mkdir -p "${dir}/opus"

  name_and_version="${dataset//[^A-Za-z0-9_- ]/_}"
  archive_path="${dir}/opus/${name_and_version}.txt.zip"

  test -s "${archive_path}" ||
    wget -O "${archive_path}" "https://object.pouta.csc.fi/OPUS-${dataset}/moses/${src}-${trg}.txt.zip" ||
    wget -O "${archive_path}" "https://object.pouta.csc.fi/OPUS-${dataset}/moses/${trg}-${src}.txt.zip"
  unzip -o "${archive_path}" -d "${dir}"

  rm -rf "${dir}/opus"
fi

echo "###### Done: Downloading opus corpus"

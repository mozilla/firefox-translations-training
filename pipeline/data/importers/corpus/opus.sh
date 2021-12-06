#!/bin/bash
##
# Downloads corpus using opus
#

set -x
set -euo pipefail

echo "###### Downloading opus corpus"

src=$1
trg=$2
output_prefix=$3
dataset=$4

name=${dataset%%/*}
name_and_version="${dataset//[^A-Za-z0-9_- ]/_}"

tmp="$(dirname "${output_prefix}")/opus/${name_and_version}"
mkdir -p "${tmp}"

archive_path="${tmp}/${name}.txt.zip"

wget -O "${archive_path}" "https://object.pouta.csc.fi/OPUS-${dataset}/moses/${src}-${trg}.txt.zip" ||
  wget -O "${archive_path}" "https://object.pouta.csc.fi/OPUS-${dataset}/moses/${trg}-${src}.txt.zip"
unzip -o "${archive_path}" -d "${tmp}"

for lang in ${src} ${trg}; do
  pigz -c "${tmp}/${name}.${src}-${trg}.${lang}" > "${output_prefix}.${lang}.gz" ||
    pigz -c "${tmp}/${name}.${trg}-${src}.${lang}" > "${output_prefix}.${lang}.gz"
done

rm -rf "${tmp}"


echo "###### Done: Downloading opus corpus"

#!/bin/bash
##
# Downloads corpus using opus
#
# Usage:
#   bash opus.sh source target dir dataset
#

set -x
set -euo pipefail

echo "###### Downloading opus corpus"

src=$1
trg=$2
dir=$3
dataset=$4

mkdir -p "${dir}/tmp"

dataset_path=${dir}/tmp/${dataset%\/*}.txt.zip
test -s "${dataset_path}" ||
  wget -O "${dataset_path}" "https://object.pouta.csc.fi/${dataset}/moses/${src}-${trg}.txt.zip" ||
  wget -O "${dataset_path}" "https://object.pouta.csc.fi/${dataset}/moses/${trg}-${src}.txt.zip"
unzip -o "${dataset_path}" -d "${dir}"

rm -rf "${dir}/tmp"

echo "###### Done: Downloading opus corpus"

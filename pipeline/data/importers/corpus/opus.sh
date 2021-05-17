#!/bin/bash
# Downloads corpus using opus
#
# Usage:
#   bash opus.sh source target dir dataset
#

set -x
set -euo pipefail

src=$1
trg=$2
dir=$3
dataset=$4

mkdir -p ${dir}/tmp

dataset_path=${dir}/tmp/${dataset%\/*}.txt.zip
wget -nc -O "$dataset_path"  https://object.pouta.csc.fi/${dataset}/moses/"${src}"-"${trg}".txt.zip || \
rm $dataset_path && \
wget -nc -O "$dataset_path"  https://object.pouta.csc.fi/${dataset}/moses/"${trg}"-"${src}".txt.zip
unzip "$dataset_path" -d ${dir}

rm -rf ${dir}/tmp
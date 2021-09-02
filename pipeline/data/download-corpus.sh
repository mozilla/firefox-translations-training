#!/bin/bash
##
# Downloads corpus datasets
#

set -x
set -euo pipefail

echo "###### Downloading corpus"

test -v SRC
test -v TRG

prefix=$1
cache=$2
id=$3
datasets=( "${@:4}" )

src_corpus="${prefix}.${SRC}.gz"
trg_corpus="${prefix}.${TRG}.gz"
dir=$(dirname "${prefix}")/${id}

mkdir -p "${dir}"

echo "### Downloading datasets"

for dataset in "${datasets[@]}"; do
  echo "### Downloading dataset ${dataset}"
  name=${dataset#*_}
  type=${dataset%%_*}
  bash "pipeline/data/importers/corpus/${type}.sh" "${SRC}" "${TRG}" "${dir}" "${name}"
done

cat "${dir}"/*."${SRC}" | pigz >"${src_corpus}"
cat "${dir}"/*."${TRG}" | pigz >"${trg_corpus}"


rm -rf "${dir}"

echo "###### Done: Downloading corpus"

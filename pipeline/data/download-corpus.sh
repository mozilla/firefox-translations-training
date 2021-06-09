#!/bin/bash
##
# Downloads corpus datasets
#
# Usage:
#   bash download-corpus.sh output_prefix dataset [dataset...]
#

set -x
set -euo pipefail

echo "###### Downloading corpus"

test -v SRC
test -v TRG

prefix=$1

src_corpus="${prefix}.${SRC}.gz"
trg_corpus="${prefix}.${TRG}.gz"
dir=$(dirname "${prefix}")

mkdir -p "${dir}"

if [ ! -e "${trg_corpus}" ]; then
  echo "### Downloading datasets"
  mkdir -p "${dir}/train-parts"

  for dataset in "${@:2}"; do
    echo "Downloading dataset ${dataset}"
    name=${dataset#*_}
    type=${dataset%_*}
    bash "${WORKDIR}/pipeline/data/importers/corpus/${type}.sh" "${SRC}" "${TRG}" "${dir}" "${name}"
  done

  cat "${dir}"/train-parts/*."${SRC}" | pigz >"${src_corpus}"
  cat "${dir}"/train-parts/*."${TRG}" | pigz >"${trg_corpus}"

else
  echo "Datasets already exist"
fi

test -s "${src_corpus}" || exit 1
test -s "${trg_corpus}" || exit 1

rm -rf "${dir}"/train-parts

echo "###### Done: Downloading corpus"

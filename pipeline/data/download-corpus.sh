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
cache=$2

src_corpus="${prefix}.${SRC}.gz"
trg_corpus="${prefix}.${TRG}.gz"
dir=$(dirname "${prefix}")/tmp

mkdir -p "${dir}"

if [ ! -e "${trg_corpus}" ]; then
  echo "### Downloading datasets"

  for dataset in "${@:2}"; do
    echo "### Downloading dataset ${dataset}"
    name=${dataset#*_}
    type=${dataset%%_*}
    bash "${WORKDIR}/pipeline/data/importers/corpus/${type}.sh" "${SRC}" "${TRG}" "${dir}" "${name}"
  done

  cat "${dir}"/*."${SRC}" | pigz >"${src_corpus}"
  cat "${dir}"/*."${TRG}" | pigz >"${trg_corpus}"

else
  echo "### Datasets already exist"
fi

test -s "${src_corpus}" || exit 1
test -s "${trg_corpus}" || exit 1

rm -rf "${dir}"

echo "###### Done: Downloading corpus"

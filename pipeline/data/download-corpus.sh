#!/bin/bash
##
# Downloads parallel dataset
#

set -x
set -euo pipefail

test -v SRC
test -v TRG


dataset=$1
output=$2

echo "### Downloading dataset ${dataset}"

dir=$(dirname "${output}")
mkdir -p "${dir}"

name=${dataset#*_}
type=${dataset%%_*}
bash "pipeline/data/importers/corpus/${type}.sh" "${SRC}" "${TRG}" "${output}" "${name}"

echo "### Downloading dataset ${dataset}"

#!/bin/bash
##
# Downloads parallel dataset
#

set -x
set -euo pipefail

test -v SRC
test -v TRG


dataset=$1
output_prefix=$2

echo "### Downloading dataset ${dataset}"

dir=$(dirname "${output_prefix}")
mkdir -p "${dir}"

name=${dataset#*_}
type=${dataset%%_*}
bash "pipeline/data/importers/corpus/${type}.sh" "${SRC}" "${TRG}" "${output_prefix}" "${name}"

echo "### Downloading dataset ${dataset}"

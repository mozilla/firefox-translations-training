#!/bin/bash
##
# Installs and compiles marian
#
# Usage:
#   bash compile-marian.sh
#

set -x
set -euo pipefail

echo "###### Compiling marian"

test -v MARIAN
test -v CUDA_DIR

threads=$1

mkdir -p "${MARIAN}"
cd "${MARIAN}"
cmake .. -DUSE_SENTENCEPIECE=on -DUSE_FBGEMM=on -DCOMPILE_CPU=on -DCMAKE_BUILD_TYPE=Release \
  -DCUDA_TOOLKIT_ROOT_DIR="${CUDA_DIR}"
make -j "${threads}"

echo "###### Done: Compiling marian"

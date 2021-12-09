#!/bin/bash
##
# Installs and compiles marian
#

set -x
set -euo pipefail

echo "###### Compiling marian"

test -v CUDA_DIR

marian_dir=$1
threads=$2

mkdir -p "${marian_dir}"
cd "${marian_dir}"
cmake .. -DUSE_SENTENCEPIECE=on -DUSE_FBGEMM=on -DCOMPILE_CPU=on -DCMAKE_BUILD_TYPE=Release \
  -DCUDA_TOOLKIT_ROOT_DIR="${CUDA_DIR}" -DBUILD_ARCH=core-avx2
make -j "${threads}"

echo "###### Done: Compiling marian"

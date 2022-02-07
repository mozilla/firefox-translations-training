#!/bin/bash
##
# Installs and compiles alignment tools
#

set -x
set -euo pipefail

echo "###### Compiling preprocess"

test -v BIN

build_dir=$1
threads=$2

mkdir -p "${build_dir}"
cd "${build_dir}"
cmake .. -DBUILD_TYPE=Release
make -j "${threads}"
cp bin/dedupe "${BIN}"

echo "###### Done: Compiling preprocess"

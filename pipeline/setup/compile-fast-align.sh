#!/bin/bash
##
# Installs and compiles alignment tools
#

set -x
set -euo pipefail

echo "###### Compiling fast align"

test -v BIN

build_dir=$1
threads=$2


mkdir -p "${BIN}"
mkdir -p "${build_dir}"
cd "${build_dir}"
cmake ..
make -j "${threads}"
cp fast_align atools "${BIN}"

echo "###### Done: Compiling fast align"

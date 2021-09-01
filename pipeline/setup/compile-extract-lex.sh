#!/bin/bash
##
# Installs and compiles alignment tools
#

set -x
set -euo pipefail

echo "###### Compiling extract-lex"

test -v BIN

build_dir=$1
threads=$2

mkdir -p "${BIN}"
mkdir -p "${build_dir}"
cd "${build_dir}"
cmake ..
make -j "${threads}"
cp extract_lex "${BIN}"


echo "###### Done: Compiling extract-lex"

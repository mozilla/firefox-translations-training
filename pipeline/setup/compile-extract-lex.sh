#!/bin/bash
##
# Installs and compiles alignment tools
#
# Usage:
#   bash compile-extract-lex.sh
#

set -x
set -euo pipefail

echo "###### Compiling extract-lex"

test -v THREADS
test -v BIN
test -v BUILD_DIR

mkdir -p "${BIN}"
mkdir -p "${BUILD_DIR}"
cd "${BUILD_DIR}"
cmake ..
make -j "${THREADS}"
cp extract_lex "${BIN}"


echo "###### Done: Compiling extract-lex"

#!/bin/bash
##
# Installs and compiles alignment tools
#
# Usage:
#   bash compile-fast-align.sh
#

set -x
set -euo pipefail

test -v BIN
test -v BUILD_DIR
test -v THREADS

echo "###### Compiling fast align"

echo "### Installing fast_align dependencies "
apt-get install -y libgoogle-perftools-dev libsparsehash-dev libboost-all-dev

echo "### Compiling fast_align"
mkdir -p "${BIN}"
mkdir -p "${BUILD_DIR}"
cd "${BUILD_DIR}"
cmake ..
make -j "${THREADS}"
cp fast_align atools "${BIN}"


echo "###### Done: Compiling fast align"

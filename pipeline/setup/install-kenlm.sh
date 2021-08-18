#!/bin/bash
##
# Installs and compiles kenlm
#
# Usage:
#   bash install-kenlm.sh
#

set -x
set -euo pipefail

echo "###### Installing kenlm"
test -v KENLM
test -v BIN
test -v THREADS

cd "${KENLM}"
mkdir -p build
cd build
mkdir "${BIN}/kenlm"
cmake .. -DKENLM_MAX_ORDER=7 -DCMAKE_INSTALL_PREFIX:PATH="${BIN}/kenlm"
make -j "${THREADS}" install
cd ..

python -m pip install . --install-option="--max_order 7"

echo "###### Done: Installing kenlm"

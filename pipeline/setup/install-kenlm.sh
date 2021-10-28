#!/bin/bash
##
# Installs and compiles kenlm
#

set -x
set -euo pipefail

echo "###### Installing kenlm"

test -v BIN

kenlm=$1
threads=$2

cd "${kenlm}"
mkdir -p build
cd build
mkdir "${BIN}/kenlm"
cmake .. -DKENLM_MAX_ORDER=7 -DCMAKE_INSTALL_PREFIX:PATH="${BIN}/kenlm"
make -j "${threads}" install
cd ..

python -m pip install . --install-option="--max_order 7"

echo "###### Done: Installing kenlm"

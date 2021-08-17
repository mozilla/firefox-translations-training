#!/bin/bash
##
# Installs and compiles kenlm
#
# Usage:
#   bash install-kenlm.sh
#

set -x
set -euo pipefail

threads=$1

echo "###### Installing kenlm"
test -v WORKDIR
test -v BIN

cd "${WORKDIR}/3rd_party/kenlm"

if [ ! -e "${BIN}/kenlm" ]; then
  mkdir -p build
  cd build
  mkdir "${BIN}/kenlm"
  cmake .. -DKENLM_MAX_ORDER=7 -DCMAKE_INSTALL_PREFIX:PATH="${BIN}/kenlm"
  make -j "${threads}" install
  cd ..
fi

python -m pip install . --install-option="--max_order 7"

echo "###### Done: Installing kenlm"

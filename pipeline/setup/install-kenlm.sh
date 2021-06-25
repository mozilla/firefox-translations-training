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
test -v WORKDIR
test -v BIN

if [ ! -e "${BIN}/kenlm" ]; then
  cd "${WORKDIR}/3rd_party/kenlm"
  source "${WORKDIR}/pipeline/setup/activate-python.sh"
  python -m pip install . --install-option="--max_order 7"

  mkdir -p build
  cd build
  mkdir "${BIN}/kenlm"
  cmake .. -DKENLM_MAX_ORDER=7 -DCMAKE_INSTALL_PREFIX:PATH="${BIN}/kenlm"
  make -j all install
  cd "${WORKDIR}"
fi

echo "###### Done: Installing kenlm"

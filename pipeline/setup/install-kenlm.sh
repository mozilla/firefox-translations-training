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

  PATH="/root/miniconda3/bin:${PATH}"
  source /root/miniconda3/etc/profile.d/conda.sh
  conda activate bergamot-training-env
  python -m pip install . --install-option="--max_order 7"

  mkdir -p build
  cd build
  cmake .. -DKENLM_MAX_ORDER=7 -DCMAKE_INSTALL_PREFIX:PATH="${BIN}"
  make -j all install
  cd "${WORKDIR}"
fi

echo "###### Done: Installing kenlm"

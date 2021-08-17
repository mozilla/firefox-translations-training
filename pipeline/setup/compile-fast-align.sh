#!/bin/bash
##
# Installs and compiles alignment tools
#
# Usage:
#   bash compile-fast-align.sh $(nproc)
#

set -x
set -euo pipefail

threads=$1

echo "###### Compiling fast align"

echo "### Installing fast_align dependencies "
apt-get install -y libgoogle-perftools-dev libsparsehash-dev libboost-all-dev
mkdir -p "${BIN}"

if [ ! -e "${WORKDIR}/bin/fast_align" ]; then
  echo "### Compiling fast_align"
  mkdir -p "${WORKDIR}/3rd_party/fast_align/build"
  cd "${WORKDIR}/3rd_party/fast_align/build"
  cmake ..
  make -j "${threads}"
  cp fast_align atools "${BIN}"
fi

echo "###### Done: Compiling fast align"

#!/bin/bash
##
# Create python conda environment
#
# Usage:
#   bash install-conda.sh
#

set -x
set -euo pipefail

echo "###### Installing Conda"

if [ ! -e "${CONDA_DIR}/bin/conda" ]; then
  wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
  bash ./Miniconda3-latest-Linux-x86_64.sh -b -u -p "${CONDA_DIR}"
  rm -f Miniconda3-latest-Linux-x86_64.sh
fi
export PATH="${CONDA_DIR}/bin:${PATH}"


echo "###### Done: Installing Conda"

#!/bin/bash
##
# Create python conda environment
#
# Usage:
#   bash install-python.sh
#

set -x
set -euo pipefail

echo "###### Installing Python"

if [ ! -e "${CONDA_DIR}/bin/conda" ]; then
  wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
  bash ./Miniconda3-latest-Linux-x86_64.sh -b -u -p "${CONDA_DIR}"
  rm -f Miniconda3-latest-Linux-x86_64.sh
fi
export PATH="${CONDA_DIR}/bin:${PATH}"
conda create -y --name bergamot-training-env python=3.8


echo "###### Done: Installing Python"

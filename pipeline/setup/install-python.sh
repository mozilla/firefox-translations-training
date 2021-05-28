#!/bin/bash
# Install and compiles dependencies
#

set -x
set -euo pipefail

echo "--- Installing Python libraries ---"
if [ ! -e /root/miniconda3/bin/conda ]; then
  wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
  bash ./Miniconda3-latest-Linux-x86_64.sh -b -u
  rm -f Miniconda3-latest-Linux-x86_64.sh
fi
export PATH="/root/miniconda3/bin:${PATH}"
conda create -y --name bergamot-training-env python=3.8
source /root/miniconda3/etc/profile.d/conda.sh
conda activate bergamot-training-env
pip install -r "${WORKDIR}"/pipeline/setup/requirements.txt

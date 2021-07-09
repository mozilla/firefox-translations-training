#!/bin/bash
##
# Activates python conda environment
#
# Usage:
#   source ./activate-python.sh
#

set +eu
PATH="${CONDA_DIR}/bin:${PATH}"
source "${CONDA_DIR}/etc/profile.d/conda.sh"
conda activate bergamot-training-env
set -eu
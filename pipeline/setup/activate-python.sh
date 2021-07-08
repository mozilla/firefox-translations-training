#!/bin/bash
##
# Activates python conda environment
#
# Usage:
#   source ./activate-python.sh
#

PATH="${BIN}/miniconda3/bin:${PATH}"
source "${BIN}/miniconda3/etc/profile.d/conda.sh"
conda activate bergamot-training-env
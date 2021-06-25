#!/bin/bash
##
# Activates python conda environment
#
# Usage:
#   source ./activate-python.sh
#

PATH="/root/miniconda3/bin:${PATH}"
source /root/miniconda3/etc/profile.d/conda.sh
conda activate bergamot-training-env
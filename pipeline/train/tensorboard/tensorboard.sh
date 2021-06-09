#!/bin/bash
##
# Runs tensorboard on 6006
#
# Usage:
#   Run from current directory
#   MODELS=<absolute_path_to_models_directory> bash tensorboard.sh
#

set -x
set -euo pipefail

echo "###### Running tensorboard"

test -v MODELS

PATH="/root/miniconda3/bin:${PATH}"
source /root/miniconda3/etc/profile.d/conda.sh
conda activate bergamot-training-env

ls -d "${MODELS}"/*/* > tb-monitored-jobs
tensorboard --logdir="${MODELS}" --host=0.0.0.0 &
python ./tb_log_parser.py --prefix=

echo "###### Done: Running tensorboard"
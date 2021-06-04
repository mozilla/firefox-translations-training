#!/bin/bash
#
# Runs tensorboard on 6006
#
# Usage:
#   Run from current dir

set -x
set -euo pipefail

PATH="/root/miniconda3/bin:${PATH}"
source /root/miniconda3/etc/profile.d/conda.sh
conda activate bergamot-training-env

ls -d $(pwd)/../../../models/*/* > tb-monitored-jobs
python ./tb_log_parser.py --prefix= & \
tensorboard --logdir=$(pwd)/../../../models --host=0.0.0.0 && fg
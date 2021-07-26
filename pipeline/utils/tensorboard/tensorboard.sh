#!/bin/bash
##
# Runs tensorboard on 6006
#
# Usage:
#   Run from current directory
#   WORKDIR=<repo-root-dir> MODELS=<absolute_path_to_models_directory> bash tensorboard.sh
#

set -x
set -euo pipefail

echo "###### Running tensorboard"

test -v MODELS
test -v WORKDIR

source "${WORKDIR}/pipeline/setup/activate-python.sh"

ls -d "${MODELS}"/*/*/* > tb-monitored-jobs
tensorboard --logdir="${MODELS}" --host=0.0.0.0 &
python ./tb_log_parser.py --prefix=

echo "###### Done: Running tensorboard"
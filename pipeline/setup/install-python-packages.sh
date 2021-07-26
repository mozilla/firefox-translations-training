#!/bin/bash
##
# Install python packages
#
# Usage:
#   bash install-python-packages.sh
#

set -x
set -euo pipefail

echo "###### Installing Python packages"

source "${WORKDIR}/pipeline/setup/activate-python.sh"
pip install -r "${WORKDIR}/pipeline/setup/requirements.txt"


echo "###### Done: Installing Python packages"

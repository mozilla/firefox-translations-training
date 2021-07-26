#!/bin/bash
##
# Install and compiles all dependencies
#
# Usage:
#   bash install-all.sh
#

set -x
set -euo pipefail

echo "######### Installing all dependencies"

test -v WORKDIR

echo "### Updating git submodules"
git submodule update --init --recursive

echo "### Installing extra dependencies"
sudo apt-get install -y pigz htop wget unzip parallel

bash "${WORKDIR}/pipeline/setup/compile-marian.sh"
bash "${WORKDIR}/pipeline/setup/compile-alignment.sh"
bash "${WORKDIR}/pipeline/setup/install-python.sh"
bash "${WORKDIR}/pipeline/setup/install-kenlm.sh"
bash "${WORKDIR}/pipeline/setup/install-python-packages.sh"

echo "######### Done: Installing all dependencies"

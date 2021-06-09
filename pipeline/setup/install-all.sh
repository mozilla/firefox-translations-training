#!/bin/bash
# Install and compiles all dependencies
#

set -x
set -euo pipefail

test -v WORKDIR

echo "--- Update git submodules ---"
git submodule update --init --recursive

echo "--- Installing extra dependencies ---"
sudo apt-get install -y pigz htop wget unzip parallel

bash "${WORKDIR}/pipeline/setup/compile-marian.sh"
bash "${WORKDIR}/pipeline/setup/install-python.sh"
bash "${WORKDIR}/pipeline/setup/compile-alignment.sh"

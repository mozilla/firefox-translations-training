#!/bin/bash
# Install and compiles all dependencies
#

set -x
set -euo pipefail

test -v WORKDIR


echo "--- Update git submodules ---"
git submodule init
git submodule update

echo "--- Installing extra dependencies ---"
sudo apt-get install -y pigz htop wget unzip parallel

bash ${WORKDIR}/setup/compile-marian.sh
bash ${WORKDIR}/setup/install-python.sh
bash ${WORKDIR}/setup/compile-alignment.sh




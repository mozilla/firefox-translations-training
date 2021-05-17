#!/bin/bash
# Install and compiles dependencies
#

set -x
set -euo pipefail

#test -v WORKDIR
#test -v CUDA_DIR

dir=$(dirname $0)
echo $dir

echo "--- Update git submodules ---"
git submodule init
git submodule update

echo "--- Installing extra dependencies ---"
#sudo apt-get install -y pigz htop wget unzip parallel

bash "${0}"/compile-marian.sh
bash "${0}"/install-python.sh
bash "${0}"/compile-alignment.sh




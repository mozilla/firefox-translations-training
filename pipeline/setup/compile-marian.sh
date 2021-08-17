#!/bin/bash
##
# Installs and compiles marian
#
# Usage:
#   bash compile-marian.sh $(nproc)
#

set -x
set -euo pipefail

echo "###### Compiling marian"

threads=$1

#echo "### Installing Intel MKL"
#wget -qO- 'https://apt.repos.intel.com/intel-gpg-keys/GPG-PUB-KEY-INTEL-SW-PRODUCTS-2019.PUB' | apt-key add -
#sh -c 'echo deb https://apt.repos.intel.com/mkl all main > /etc/apt/sources.list.d/intel-mkl.list'
#apt-get update
#apt-get install -y intel-mkl-64bit-2020.0-088

#if [ ! -e /usr/local/bin/cmake ]; then
#  echo "### Installing CMake"
#  apt-get install -y \
#    autoconf \
#    automake
#  wget https://github.com/Kitware/CMake/releases/download/v3.20.2/cmake-3.20.2-Linux-x86_64.sh
#  chmod +x cmake-3.20.2-Linux-x86_64.sh
#  bash ./cmake-3.20.2-Linux-x86_64.sh --skip-license --prefix=/usr/local
#  rm ./cmake-3.20.2-Linux-x86_64.sh
#fi


echo "### Compiling marian-dev"

mkdir -p "${MARIAN}"
cd "${MARIAN}"
cmake .. -DUSE_SENTENCEPIECE=on -DUSE_FBGEMM=on -DCOMPILE_CPU=on -DCMAKE_BUILD_TYPE=Release \
  -DCUDA_TOOLKIT_ROOT_DIR="${CUDA_DIR}"
make -j "${threads}"

echo "###### Done: Compiling marian"

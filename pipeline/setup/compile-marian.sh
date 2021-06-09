#!/bin/bash
# Install and compiles marian
#

set -x
set -euo pipefail

echo "--- Installing marian dependencies ---"
sudo apt-get install -y git cmake build-essential libboost-system-dev libprotobuf10 \
  protobuf-compiler libprotobuf-dev openssl libssl-dev libgoogle-perftools-dev

echo "--- Installing Intel MKL ---"
wget -qO- 'https://apt.repos.intel.com/intel-gpg-keys/GPG-PUB-KEY-INTEL-SW-PRODUCTS-2019.PUB' | sudo apt-key add -
sudo sh -c 'echo deb https://apt.repos.intel.com/mkl all main > /etc/apt/sources.list.d/intel-mkl.list'
sudo apt-get update
sudo apt-get install -y intel-mkl-64bit-2020.0-088

if [ ! -e /usr/local/bin/cmake ]; then
  echo "--- Installing CMake ---"
  sudo apt-get install -y \
    autoconf \
    automake
  wget https://github.com/Kitware/CMake/releases/download/v3.20.2/cmake-3.20.2-Linux-x86_64.sh
  sudo chmod +x cmake-3.20.2-Linux-x86_64.sh
  sudo ./cmake-3.20.2-Linux-x86_64.sh --skip-license --prefix=/usr/local
  rm ./cmake-3.20.2-Linux-x86_64.sh
fi

if [ ! -e "${MARIAN}/marian" ]; then
  echo "--- Compiling marian-dev ---"
  mkdir -p "${MARIAN}"
  cd "${MARIAN}"
  /usr/local/bin/cmake .. -DUSE_SENTENCEPIECE=on -DUSE_FBGEMM=on -DCOMPILE_CPU=on -DCMAKE_BUILD_TYPE=Release \
    -DCUDA_TOOLKIT_ROOT_DIR="${CUDA_DIR}"
  make -j "$(nproc)"
  cd "${WORKDIR}"
  test -s "${MARIAN}/marian" || exit 1
fi

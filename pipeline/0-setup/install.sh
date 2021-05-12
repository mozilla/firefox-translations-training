#!/bin/bash
# Install and compiles dependencies
#

set -x
set -euo pipefail

test -v WORKDIR
test -v CUDA_DIR

echo "--- Update git submodules ---"
git submodule init
git submodule update

echo "--- Installing marian dependencies ---"
sudo apt-get install -y git cmake build-essential libboost-system-dev libprotobuf10 \
    protobuf-compiler libprotobuf-dev openssl libssl-dev libgoogle-perftools-dev

echo "--- Installing extra dependencies ---"
sudo apt-get install -y pigz htop wget

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


if [ ! -e ${WORKDIR}/marian-dev/build/marian ]; then
  echo "--- Compiling marian-dev ---"
  mkdir -p ${WORKDIR}/marian-dev/build
  cd marian-dev/build
  /usr/local/bin/cmake .. -DUSE_SENTENCEPIECE=on -DUSE_FBGEMM=on -DCOMPILE_CPU=on -DCMAKE_BUILD_TYPE=Release \
            -DCUDA_TOOLKIT_ROOT_DIR=${CUDA_DIR}
  make -j$(nproc)
  cd ../..
  test -s ${WORKDIR}/marian-dev/build/marian || exit 1
fi


echo "--- Installing Python libraries ---"
if [ ! -e /root/miniconda3/bin/conda ]; then
  wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
  bash ./Miniconda3-latest-Linux-x86_64.sh -b -u
  rm -f Miniconda3-latest-Linux-x86_64.sh
fi
export PATH="/root/miniconda3/bin:${PATH}"
conda create -y --name bergamot-training-env python=3.8
source /root/miniconda3/etc/profile.d/conda.sh
conda activate bergamot-training-env
pip install -r ${WORKDIR}/pipeline/0-setup/requirements.txt


echo "--- Installing fast_align dependencies ---"
sudo apt-get install -y libgoogle-perftools-dev libsparsehash-dev libboost-all-dev
mkdir -p ${WORKDIR}/bin



if [ ! -e ${WORKDIR}/bin/fast_align ]; then
    echo "--- Compiling fast_align ---"
    mkdir -p ${WORKDIR}/fast_align/build
    cd ${WORKDIR}/fast_align/build
    cmake ..
    make -j$(nproc)
    cp fast_align atools ../../bin
    cd ../../
    test -s ${WORKDIR}/bin/fast_align || exit 1
fi



if [ ! -e ${WORKDIR}/bin/extract_lex ]; then
    echo "--- Compiling extract-lex ---"
    mkdir -p ${WORKDIR}/extract-lex/build
    cd ${WORKDIR}/extract-lex/build
    cmake ..
    make -j$(nproc)
    cp extract_lex ../../bin
    cd ../../
    test -s ${WORKDIR}/bin/extract_lex || exit 1
fi



#!/bin/bash
# Install and compiles dependencies
#

set -x
set -euo pipefail

test -v WORKDIR
test -v CUDA_DIR


echo "Installing marian dependencies"
sudo apt-get install -y git cmake build-essential libboost-system-dev libprotobuf10 \
    protobuf-compiler libprotobuf-dev openssl libssl-dev libgoogle-perftools-dev


echo "Installing Intel MKL"
wget -qO- 'https://apt.repos.intel.com/intel-gpg-keys/GPG-PUB-KEY-INTEL-SW-PRODUCTS-2019.PUB' | sudo apt-key add -
sudo sh -c 'echo deb https://apt.repos.intel.com/mkl all main > /etc/apt/sources.list.d/intel-mkl.list'
sudo apt-get update
sudo apt-get install -y intel-mkl-64bit-2020.0-088

echo "Installing CMake"
sudo apt-get install -y \
    autoconf \
    automake
wget https://github.com/Kitware/CMake/releases/download/v3.20.2/cmake-3.20.2-Linux-x86_64.sh
sudo chmod +x cmake-3.20.2-Linux-x86_64.sh
sudo ./cmake-3.20.2-Linux-x86_64.sh --skip-license --prefix=/usr/local


echo "Compiling marian-dev"
if [ ! -e ${WORKDIR}/marian-dev/build/marian ]; then
  mkdir -p ${WORKDIR}/marian-dev/build
  cd marian-dev/build
  /usr/local/bin/cmake .. -DUSE_SENTENCEPIECE=on -DUSE_FBGEMM=on -DCOMPILE_CPU=on -DCMAKE_BUILD_TYPE=Release \
            -DCUDA_TOOLKIT_ROOT_DIR=${CUDA_DIR}
  make -j$(nproc)
  cd ../..
  test -s ${WORKDIR}/marian-dev/build/marian || exit 1
fi


echo "Installing Python libraries"
sudo apt-get install -y python3 python3-venv python3-pip
pip3 install virtualenv
python3 -m venv bergamot-training-venv
source bergamot-training-venv/bin/activate
pip3 install -r ${WORKDIR}/pipeline/0-setup/requirements.txt


echo "Installing fast_align dependencies"
sudo apt-get install libsparsehash-dev
mkdir -p ${WORKDIR}/bin


echo "Compiling fast_align"
if [ ! -e ${WORKDIR}/bin/fast_align ]; then
    mkdir -p ${WORKDIR}/fast_align/build
    cd ${WORKDIR}/fast_align/build
    cmake ..
    make -j$(nproc)
    cp fast_align atools ../../bin
    cd ../../
    test -s ${WORKDIR}/bin/fast_align || exit 1
fi


echo "Compiling extract-lex"
if [ ! -e ${WORKDIR}/bin/extract_lex ]; then
    mkdir -p ${WORKDIR}/extract-lex/build
    cd ${WORKDIR}/extract-lex/build
    cmake ..
    make -j4
    cp extract_lex ../../bin
    cd ../../
    test -s ${WORKDIR}/bin/extract_lex || exit 1
fi

echo "Installing extra dependencies"
sudo apt-get install pigz htop wget

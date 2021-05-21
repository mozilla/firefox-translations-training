#!/bin/bash
# Installs and compiles alignment tools
#

set -x
set -euo pipefail


echo "--- Installing fast_align dependencies ---"
sudo apt-get install -y libgoogle-perftools-dev libsparsehash-dev libboost-all-dev
mkdir -p "${WORKDIR}"/bin



if [ ! -e "${WORKDIR}"/bin/fast_align ]; then
    echo "--- Compiling fast_align ---"
    mkdir -p "${WORKDIR}"/3rd_party/fast_align/build
    cd "${WORKDIR}"/3rd_party/fast_align/build
    cmake ..
    make -j$(nproc)
    cp fast_align atools ${WORKDIR}/bin
    cd "${WORKDIR}"
    test -s "${WORKDIR}"/bin/fast_align || exit 1
fi



if [ ! -e "${WORKDIR}"/bin/extract_lex ]; then
    echo "--- Compiling extract-lex ---"
    mkdir -p "${WORKDIR}"/3rd_party/extract-lex/build
    cd "${WORKDIR}"/3rd_party/extract-lex/build
    cmake ..
    make -j$(nproc)
    cp extract_lex ${WORKDIR}/bin
    cd "${WORKDIR}"
    test -s "${WORKDIR}"/bin/extract_lex || exit 1
fi



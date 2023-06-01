#!/bin/bash
set -e
set -x

pushd `dirname $0` &>/dev/null
MY_DIR=$(pwd)
popd &>/dev/null

patch=${1:-none}

export MARIAN_DIR=$MOZ_FETCHES_DIR/marian-source
export CUDA_DIR=$MOZ_FETCHES_DIR/cuda-toolkit

if [ "$patch" != "none" ]; then
  patch -d ${MARIAN_DIR} -p1 < ${MY_DIR}/${patch}
fi

# TODO: consider not calling out to this since it's such a simple script...
bash $VCS_PATH/pipeline/setup/compile-marian.sh "${MARIAN_DIR}/build" "$(nproc)"

cd $MARIAN_DIR/build
tar --zstd -cf $UPLOAD_DIR/marian.tar.zst \
  "marian" \
  "marian-decoder" \
  "marian-scorer" \
  "marian-conv" \
  "spm_train" \
  "spm_encode" \
  "spm_export_vocab"

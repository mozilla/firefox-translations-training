#!/bin/bash
set -e
set -x

FAST_ALIGN_DIR=$MOZ_FETCHES_DIR/fast_align

build_dir=$(mktemp -d)
cd $build_dir
cmake $FAST_ALIGN_DIR
make -j$(nproc)

cd "${build_dir}"
chmod +x fast_align atools
tar -c fast_align atools | zstd > $UPLOAD_DIR/fast-align.tar.zst

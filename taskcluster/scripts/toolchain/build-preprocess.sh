#!/bin/bash
set -e
set -x

PREPROCESS_DIR=$MOZ_FETCHES_DIR/preprocess

build_dir=$(mktemp -d)
cd $build_dir
cmake $PREPROCESS_DIR -DBUILD_TYPE=Release
make -j$(nproc)

cd $build_dir/bin
chmod +x dedupe
tar --zstd -cf $UPLOAD_DIR/dedupe.tar.zst dedupe

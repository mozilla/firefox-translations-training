#!/bin/bash
set -e
set -x

PREPROCESS_DIR=$MOZ_FETCHES_DIR/preprocess

build_dir=$(mktemp -d)
cd $build_dir
cmake $PREPROCESS_DIR -DBUILD_TYPE=Release
make -j$(nproc)

cp $build_dir/bin/dedupe $UPLOAD_DIR

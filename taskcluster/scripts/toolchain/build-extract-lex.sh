#!/bin/bash
set -e
set -x

EXTRACT_LEX_DIR=$MOZ_FETCHES_DIR/extract-lex

build_dir=$(mktemp -d)
cd $build_dir
cmake $EXTRACT_LEX_DIR
make -j$(nproc)

cp $build_dir/extract_lex $UPLOAD_DIR

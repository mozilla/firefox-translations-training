#!/bin/bash
set -e
set -x

KENLM_DIR=$MOZ_FETCHES_DIR/kenlm-source

# TODO: I don't think we actually need the C++ stuff? just the python module
# build_dir=$(mktemp -d)
# cd $build_dir
# cmake $KENLM_DIR -DKENLM_MAX_ORDER=7
# make -j$(nproc)

cd $KENLM_DIR
# Install these separately so they will install as wheels.
# Using `--build-option` below disables wheels even for dependencies.
pip install setuptools wheel cmake
MAX_ORDER=7 python3 setup.py bdist_wheel
find .
cp $KENLM_DIR/dist/kenlm-0.0.0-cp310-cp310-linux_x86_64.whl $UPLOAD_DIR/

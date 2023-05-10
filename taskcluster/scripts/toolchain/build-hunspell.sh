#!/bin/bash
set -e
set -x

HUNSPELL_DIR=$MOZ_FETCHES_DIR/hunspell

cd $HUNSPELL_DIR
python3 setup.py bdist_wheel
whl=$(ls dist/*.whl)

cp $whl $UPLOAD_DIR/

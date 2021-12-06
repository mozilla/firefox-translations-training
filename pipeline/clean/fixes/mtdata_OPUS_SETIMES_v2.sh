#!/bin/bash
set -e

# Detokenize SETIMES

SRC=$1
TRG=$2
threads=$3

temp=$(mktemp -d)

tee >(cut -f1 | sacremoses -j $threads -l $SRC detokenize >$temp/$SRC.detok) \
    >(cut -f2 | sacremoses -j $threads -l $TRG detokenize >$temp/$TRG.detok)

paste $temp/$SRC.detok $temp/$TRG.detok

rm -r $temp

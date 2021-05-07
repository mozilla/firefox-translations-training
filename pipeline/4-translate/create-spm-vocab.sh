#!/bin/bash

MARIAN=../../marian-dev/build
SRC=en
TRG=de

# Prepare data for vocabulary.
pigz -dc data.$SRC.clean.gz | shuf | head -n 20M > data.txt
pigz -dc data.$TRG.clean.gz | shuf | head -n 20M >> data.txt

# Train.
$MARIAN/spm_train --bos_id=-1 --eos_id=0 --unk_id=1 --user_defined_symbols="" --input=data.txt --model_prefix=vocab --vocab_size=32000

# Marian uses .spm extension.
mv vocab.model vocab.$SRC$TRG.spm

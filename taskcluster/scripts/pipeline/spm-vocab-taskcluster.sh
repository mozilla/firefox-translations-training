#!/bin/bash

set -x
set -euo pipefail

[[ -v MOZ_FETCHES_DIR ]] || { echo "MOZ_FETCHES_DIR is not set"; exit 1; }
[[ -v VCS_PATH ]] || { echo "VCS_PATH is not set"; exit 1; }

if [ "$#" -ne 5 ]; then
    echo "Usage: $0 <src_locale> <trg_locale> <spm_sample_size> <spm_vocab_size> <pre_trained_vocab>"
    exit 1
fi

src_locale="$1"
trg_locale="$2"
spm_sample_size="$3"
spm_vocab_size="$4"
pre_trained_vocab="$5"

if [ "$pre_trained_vocab" == "None" ]; then
    echo "No pretrained vocab artifact detected. Training vocab..."
    export MARIAN=$MOZ_FETCHES_DIR
    # Arguments are:
    # 1) merged src corpus file
    # 2) merged trg corpus file
    # 3) output file
    # 4) sample size
    # 5) number of threads (auto = output of nproc)
    # 6) vocab_size
    "$VCS_PATH/pipeline/train/spm-vocab.sh" \
    "$MOZ_FETCHES_DIR/corpus.$src_locale.zst" \
    "$MOZ_FETCHES_DIR/corpus.$trg_locale.zst" \
    "$TASK_WORKDIR/artifacts/vocab.spm" \
    "$spm_sample_size" \
    auto \
    "$spm_vocab_size"
else
    echo "Found pre_trained_vocab. Downloading vocab.spm from $pre_trained_vocab"
    wget --tries=3 --waitretry=5 --retry-connrefused --timeout=30 -O $TASK_WORKDIR/artifacts/vocab.spm $pre_trained_vocab/vocab.spm
fi

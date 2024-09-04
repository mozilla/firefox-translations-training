#!/bin/bash
##
# Downloads corpus using sacrebleu
#

set -x
set -euo pipefail

echo "###### Downloading sacrebleu corpus"

src=$1
trg=$2
output_prefix=$3
dataset=$4

{
  set +e

  sacrebleu                         \
    --test-set "${dataset}"         \
    --language-pair "${src}-${trg}" \
    --echo src                      \
  | zstdmt -c > "${output_prefix}.${src}.zst"

  sacrebleu                         \
    --test-set "${dataset}"         \
    --language-pair "${src}-${trg}" \
    --echo ref                      \
  | zstdmt -c > "${output_prefix}.${trg}.zst"

  status=$?

  set -e
}

if [ $status -ne 0 ]; then
  echo "The first import failed, try again by switching the language pair direction."

  sacrebleu                         \
    --test-set "${dataset}"         \
    --language-pair "${trg}-${src}" \
    --echo src                      \
    | zstdmt -c > "${output_prefix}.${trg}.zst"

  sacrebleu                         \
    --test-set "${dataset}"         \
    --language-pair "${trg}-${src}" \
    --echo ref                      \
    | zstdmt -c > "${output_prefix}.${src}.zst"
fi


echo "###### Done: Downloading sacrebleu corpus"

#!/bin/bash
##
# Downloads monolingual Paracrawl data
#

set -x
set -euo pipefail

echo "###### Downloading monolingual data from Paracrawl"

lang=$1
output_prefix=$2
dataset=$3

if [[ "${lang}" == "en" ]]; then
    wget -O "${output_prefix}.gz" "https://neural.mt/data/${dataset}-mono/en-000.gz"
else
  echo "Only English language is supported at this time for Paracrawl"
  exit 1
fi

echo "###### Done: Downloading monolingual data from Paracrawl"

#!/bin/bash
# Downloads monolingual Paracrawl data
#
# Usage:
#   bash paracrawl.sh lang dir dataset
#

set -x
set -euo pipefail

lang=$1
dir=$2
dataset=$3


if [[ $lang == "en" ]]
then
  source_path=$dir/$dataset.original.$lang
  test -s $source_path.gz || wget -nc -O $source_path.gz https://neural.mt/data/$dataset-mono/en-000.gz
else
  echo "Only English language is supported at this time for paracrawl"
  exit 1
fi
#!/bin/bash
# Downloads monolingual Paracrawl data
#
# Usage:
#   bash paracrawl.sh lang dir dataset
#

set -x
set -euo pipefail

lang=${1}
output_prefix=${2}
dataset=${3}

if [[ "${lang}" == "en" ]]; then
  test -s "${output_prefix}.gz" ||
    wget -O "${output_prefix}.gz" "https://neural.mt/data/${dataset}-mono/en-000.gz"
else
  echo "Only English language is supported at this time for paracrawl"
  exit 1
fi

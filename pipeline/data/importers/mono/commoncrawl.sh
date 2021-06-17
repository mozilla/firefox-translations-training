#!/bin/bash
##
# Downloads monolingual data from commoncrawl
#
# Usage:
#   bash commoncrawl.sh lang output_prefix dataset
#

set -x
set -euo pipefail

echo "###### Downloading commoncrawl monolingual data"

lang=$1
output_prefix=$2
dataset=$3

test -s "${output_prefix}.gz" ||
  wget -O "${output_prefix}.xz" \
    "http://web-language-models.s3-website-us-east-1.amazonaws.com/${dataset}/deduped/${lang}.xz"
xzcat "${output_prefix}.xz" | pigz >"${output_prefix}.gz"

echo "###### Done: Downloading commoncrawl monolingual data"

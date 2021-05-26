#!/bin/bash
# Downloads monolingual data from OPUS
#
# Usage:
#   bash opus.sh lang output_prefix dataset
#


set -x
set -euo pipefail

lang=$1
output_prefix=$2
dataset=$3


test -s $output_prefix.gz || \
wget -O $output_prefix.gz http://data.statmt.org/news-crawl/${lang}/${dataset}.${lang}.shuffled.deduped.gz

#!/bin/bash
# Downloads monolingual data from OPUS
#
# Usage:
#   bash opus.sh lang dir dataset
#


set -x
set -euo pipefail

lang=$1
dir=$2
dataset=$3


test -s $source_path.gz || \
wget -O $source_path.gz http://data.statmt.org/news-crawl/${lang}/${name}.${lang}.shuffled.deduped.gz

#!/bin/bash
##
# Downloads monolingual data from WMT news crawl
#

set -x
set -euo pipefail

lang=$1
output_prefix=$2
dataset=$3

echo "###### Downloading WMT newscrawl monolingual data"

wget -O "${output_prefix}.gz" \
    "http://data.statmt.org/news-crawl/${lang}/${dataset}.${lang}.shuffled.deduped.gz"

echo "###### Done: Downloading WMT newscrawl monolingual data"

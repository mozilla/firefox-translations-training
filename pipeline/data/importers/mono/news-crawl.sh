#!/bin/bash
##
# Downloads monolingual data from WMT news crawl
#

set -x
set -euo pipefail

lang=$1
output_prefix=$2
dataset=$3

COMPRESSION_CMD="${COMPRESSION_CMD:-pigz}"
ARTIFACT_EXT="${ARTIFACT_EXT:-gz}"

echo "###### Downloading WMT newscrawl monolingual data"

curl -L "http://data.statmt.org/news-crawl/${lang}/${dataset}.${lang}.shuffled.deduped.gz" | \
    gunzip | ${COMPRESSION_CMD} -c > "${output_prefix}.${ARTIFACT_EXT}"

echo "###### Done: Downloading WMT newscrawl monolingual data"


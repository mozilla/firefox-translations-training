#!/bin/bash
# Downloads monolingual data from commoncrawl
#
# Usage:
#   bash commoncrawl.sh lang dir dataset
#

set -x
set -euo pipefail

lang=$1
dir=$2
dataset=$3

source_path=$dir/$dataset.original.$lang

test -s $source_path.xz || \
wget -O $source_path.xz http://web-language-models.s3-website-us-east-1.amazonaws.com/${name}/deduped/${lang}.xz
xzcat $source_path.xz | pigz > $source_path.gz
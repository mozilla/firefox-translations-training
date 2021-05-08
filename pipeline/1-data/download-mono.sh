#!/bin/bash
# Downloads datasets
#
# Usage:
#   bash download-mono.sh lang max_sentences output_dir
#

set -x
set -euo pipefail

lang=$1
max_sent=$2
output_dir=$3

source_file_name=${output_dir}/mono.source.${lang}.gz
file_name=${output_dir}/mono.${lang}.gz

echo "Downloading monolingual corpus for ${lang}"
if [[$lang == "en"]]; then
  wget -nc -O $source_file_name https://neural.mt/data/paracrawl8-mono/en-000.gz
  zcat $source_file_name | shuf -n ($max_sent+$max_sent*0.1) | perl -ne 'print if(split(/\s/, $_) < 100)' | \
       head -n $max_sent | pigz > $file_name
else
  echo "Only English language is supported at this time"
fi

lines=$(wc -l $file_name)
echo "Done. Number of sentences: ${lines}"

#!/bin/bash
# Downloads datasets
#
# Usage:
#   bash download-mono.sh lang max_sentences output_prefix dataset [dataset...]
#

set -x
set -euo pipefail

lang=$1
max_sent=$2
prefix=$3
datasets=${@:4}


file_name=$prefix.${lang}.gz
dir=$(dirname $prefix)/mono

if [ ! -e ${file_name} ]; then
  echo "Downloading monolingual corpus for ${lang}"
  mkdir -p $dir
  coef=0.1

  for dataset in $datasets; do
    echo "Downloading dataset ${dataset}"
    name=${dataset#*_}
    source_path=$dir/$dataset.original.$lang
    gz_path=$dir/$dataset.$lang.gz

    if [[ $dataset == news-crawl_* ]]; then
      test -s $source_path.gz || wget -O $source_path.gz http://data.statmt.org/news-crawl/${lang}/${name}.${lang}.shuffled.deduped.gz
    elif [[ $dataset == commoncrawl_* ]]; then
      test -s $source_path.xz || wget -O $source_path.xz http://web-language-models.s3-website-us-east-1.amazonaws.com/${name}/deduped/${lang}.xz
      xzcat $source_path.xz | pigz > $source_path.gz
    elif [[ $dataset == paracrawl_* ]]; then
      if [[ $lang == "en" ]]
      then
        test -s $source_path.gz || wget -nc -O $source_path.gz https://neural.mt/data/${name}-mono/en-000.gz
      else
        echo "Only English language is supported at this time for paracrawl"
        exit 1
      fi
    fi

    test -s $gz_path || zcat $source_path.gz | shuf -n $(bc -l <<< "${max_sent}+${max_sent}*${coef}") | perl -ne 'print if(split(/\s/, $_) < 100)' | \
         head -n "$max_sent" | pigz > $gz_path

    rm $source_path.*
  done

  zcat ${dir}/*.$lang.gz | pigz > $file_name

fi

test -s $file_name

lines=$(zcat $file_name | wc -l)
echo "Done. Number of sentences: ${lines}"

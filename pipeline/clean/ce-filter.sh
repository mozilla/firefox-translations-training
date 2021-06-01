#!/bin/bash
# Filtering student parallel data with a reversed NMT model.
#
# Usage:
#   bash ce-clean.sh model_dir corpus_prefix output_prefix
#


set -x
set -euo pipefail

clean_tools=${CLEAN_TOOLS:-./tools}

test -v MARIAN
test -v GPUS
test -v SRC
test -v TRG

model_dir=$1
corpus_prefix=$2
output_prefix=$3


# Part of the data to be removed (0.05 is 5%)
REMOVE=0.05
config=${model_dir}/model.npz.best-ce-mean-words.npz.decoder.yml
dir=$(dirname output_prefix)/scored
mkdir -p ${dir}

${MARIAN}/marian-scorer -c $config -t $corpus_prefix.${TRG}.gz $corpus_prefix.${SRC}.gz \
  -d ${GPUS} --log $dir/scores.txt.log > $dir/scores.txt

cat $dir/scores.txt | parallel --no-notice --pipe -k -j $(nproc) --block 50M \
  "python ${clean_tools}/normalize-scores.py" | cut -f1 > $dir/scores.nrm.txt

cat $dir/scores.nrm.txt | LC_ALL=C sort -n -k1,1 -S 10G | pigz > $dir/sorted.gz

startline=$(pigz -dc $dir/sorted.gz | wc -l | sed "s|$$|*${REMOVE}|" | bc | cut -f1 -d.)
pigz -dc $dir/sorted.gz | tail -n +${startline} | cut -f2,3 | pigz > $dir/best.gz


# todo: write output corpus

#rm -f $dir/*.scores.txt
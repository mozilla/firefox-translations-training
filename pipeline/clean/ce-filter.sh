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
model=${model_dir}/model.npz.best-ce-mean-words.npz
vocab=${model_dir}/vocab.spm
dir=$(dirname $output_prefix)/scored
mkdir -p ${dir}

${MARIAN}/marian-scorer -m $model -v $vocab $vocab -t $corpus_prefix.${TRG}.gz $corpus_prefix.${SRC}.gz \
  --mini-batch 32 --mini-batch-words 1500 --maxi-batch 1000 --max-length 250 --max-length-crop \
  -d ${GPUS} -w ${WORKSPACE} --log $dir/scores.txt.log > $dir/scores.txt

test -s $dir/scores.nrm.txt || \
paste $dir/scores.txt $corpus_prefix.${TRG}.gz \
  | parallel --no-notice --pipe -k -j $(nproc) --block 50M "python ${clean_tools}/normalize-scores.py" \
  | cut -f1 > $dir/scores.nrm.txt

test -s $dir/sorted.gz || \
paste $dir/scores.nrm.txt $corpus_prefix.${SRC}.gz $corpus_prefix.${TRG}.gz \
  | LC_ALL=C sort -n -k1,1 -S 10G \
  | pigz > $dir/sorted.gz

test -s $dir/best.gz || \
startline=$(pigz -dc $dir/sorted.gz | wc -l | sed "s|$$|*${REMOVE}|" | bc | cut -f1 -d.); \
pigz -dc $dir/sorted.gz | tail -n +${startline} | cut -f2,3 | pigz > $dir/best.gz

pigz -dc $dir/best.gz | cut -f1 | pigz > $output_prefix.$SRC.gz
pigz -dc $dir/best.gz | cut -f2 | pigz > $output_prefix.$TRG.gz

#rm -rf $dir
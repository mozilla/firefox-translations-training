#!/bin/bash

# Usage: ./translate-mono.sh mono_path model_dir output_path

set -x
set -euo pipefail


test -v GPUS
test -v MARIAN


mono_path=$1
model_dir=$2
output_path=$3

config=${model_dir}/model.npz.best-ce-mean-words.npz.decoder.yml
decoder_config=${WORKDIR}/pipeline/translate/decoder.yml
tmp_dir=$(dirname $output_path)/tmp
mkdir -p $tmp_dir


# Split the corpus into smaller chunks.
test -s $tmp_dir/file.00 || pigz -dc $mono_path | split -d -l 2000000 - $tmp_dir/file.

# Translate source sentences with Marian.
# This can be parallelized across several GPU machines.
for prefix in `ls ${tmp_dir}/file.?? | shuf`; do
    echo "# $prefix"
    test -e $prefix.out || \
    $MARIAN/marian-decoder -c $config $decoder_config -i $prefix -o $prefix.out --log $prefix.log \
    -d $GPUS -w $WORKSPACE
done

# Collect translations.
cat $tmp_dir/file.??.out | pigz > $output_path

# Source and artificial target files must have the same number of sentences,
# otherwise collect the data manually.
echo "# sentences $mono_path vs $output_path"
pigz -dc $mono_path | wc -l
pigz -dc $output_path | wc -l

rm -rf $tmp_dir


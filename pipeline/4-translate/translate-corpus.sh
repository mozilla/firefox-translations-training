#!/bin/bash

# Usage: ./translate-corpus.sh -d 4 5 6 7

set -e

# Adjust variables if needed.
MARIAN=../../marian-dev/build
CORPUSSRC=corpus.en.gz
CORPUSTRG=corpus.es.gz
CONFIG=teacher.yml
DIR=corpus
OUTPUT=$DIR.translated.gz

mkdir -p $DIR


# Split parallel corpus into smaller chunks.
test -s $DIR/file.00     || pigz -dc $CORPUSSRC | split -d -l 2000000 - $DIR/file.
test -s $DIR/file.00.ref || pigz -dc $CORPUSTRG | split -d -l 2000000 - $DIR/file. --additional-suffix .ref

# Translate source sentences with Marian.
# This can be parallelized across several GPU machines.
for prefix in `ls $DIR/file.?? | shuf`; do
    echo "# $prefix"
    test -e $prefix.nbest || $MARIAN/marian-decoder -c $CONFIG -i $prefix -o $prefix.nbest --log $prefix.log -b 8 --n-best $@
done

# Extract best translations from n-best lists w.r.t to the reference.
# It is CPU-only, can be run after translation on a CPU machine.
for prefix in `ls $DIR/file.??`; do
    echo "# $prefix"
    test -e $prefix.nbest.out || python3 bestbleu.py -i $prefix.nbest -r $prefix.ref -m bleu > $prefix.nbest.out
done

# Collect translations.
cat $DIR/file.??.nbest.out | pigz > $OUTPUT

# Source and artificial target files must have the same number of sentences,
# otherwise collect the data manually.
echo "# sentences $CORPUSSRC vs $OUTPUT"
pigz -dc $CORPUSSRC | wc -l
pigz -dc $OUTPUT | wc -l


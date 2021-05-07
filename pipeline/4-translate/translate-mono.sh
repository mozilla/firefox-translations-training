#!/bin/bash

# Usage: ./translate-mono.sh -d 4 5 6 7

set -e

# Adjust these variables if needed.
MARIAN=../../marian-dev/build
CORPUSSRC=mono.en.gz
CONFIG=teacher.yml
DIR=mono
OUTPUT=$DIR.translated.gz

mkdir -p $DIR


# Split the corpus into smaller chunks.
test -s $DIR/file.00 || pigz -dc $CORPUSSRC | split -d -l 2000000 - $DIR/file.

# Translate source sentences with Marian.
# This can be parallelized across several GPU machines.
for prefix in `ls $DIR/file.?? | shuf`; do
    echo "# $prefix"
    test -e $prefix.out || $MARIAN/marian-decoder -c $CONFIG -i $prefix -o $prefix.out --log $prefix.log -b 4 $@
done

# Collect translations.
cat $DIR/file.??.out | pigz > $OUTPUT

# Source and artificial target files must have the same number of sentences,
# otherwise collect the data manually.
echo "# sentences $CORPUSSRC vs $OUTPUT"
pigz -dc $CORPUSSRC | wc -l
pigz -dc $OUTPUT | wc -l


#!/bin/bash
##
# Basic cleaning of parallel corpora.
#
# Usage:
#   bash clean-corpus.sh prefix_input prefix_output
#

set -x
set -euo pipefail

test -v CLEAN_TOOLS
test -v SRC
test -v TRG

data=$1
output=$2

mkdir -p $(dirname $output)

# Check if files exist
test -s $data.$SRC.gz || exit 1
test -s $data.$TRG.gz || exit 1

######################################################################
# Basic preprocessing
for lng in $SRC $TRG; do
    pigz -dc $data.$lng.gz \
        | parallel --no-notice --pipe -k -j16 --block 50M "perl $CLEAN_TOOLS/remove-non-printing-char.perl | perl $CLEAN_TOOLS/normalize-punctuation.perl -l $lng" \
        | pigz > $output.$lng.nrm.gz
done

test -s $output.$SRC.nrm.gz || exit 1
test -s $output.$TRG.nrm.gz || exit 1

######################################################################
# Deduplication
paste <(pigz -dc $output.$SRC.nrm.gz) <(pigz -dc $output.$TRG.nrm.gz) \
    | LC_ALL=C sort -S 10G | uniq \
    | pigz > $output.$SRC$TRG.nrm.uniq.gz

test -s $output.$SRC$TRG.nrm.uniq.gz || exit 1

######################################################################
# Rule-based filtering
pigz -dc $output.$SRC$TRG.nrm.uniq.gz \
    | parallel --no-notice --pipe -k -j16 --block 50M "python3 $CLEAN_TOOLS/clean-parallel.py -l1 $SRC -l2 $TRG --debug" \
    2> $output.$SRC$TRG.clean.debug.txt \
    | pigz > $output.$SRC$TRG.rule-based.gz

test -s $output.$SRC$TRG.rule-based.gz || exit 1

######################################################################
# Language identification
pigz -dc $output.$SRC$TRG.rule-based.gz \
    | parallel --no-notice --pipe -k -j16 --block 50M "python3 -Wi $CLEAN_TOOLS/langid-fasttext.py -f 1 | python3 -Wi $CLEAN_TOOLS/langid-fasttext.py -f 1" \
    | grep -P "^$SRC\t$TRG\t" \
    | cut -f3,4 \
    | pigz > $output.$SRC$TRG.langid.gz

test -s $output.$SRC$TRG.langid.gz

######################################################################
# Generate clean data in source and target languages
# Remove leading and repetitive white spaces
pigz -dc $output.$SRC$TRG.langid.gz | cut -f1 | sed -e 's/^[[:space:]]*//' | tr -s " " \
    | pigz > $output.$SRC.clean.gz
pigz -dc $output.$SRC$TRG.langid.gz | cut -f2 | sed -e 's/^[[:space:]]*//' | tr -s " " \
    | pigz > $output.$TRG.clean.gz

test -s $output.$SRC.clean.gz || exit 1
test -s $output.$TRG.clean.gz || exit 1

# Remove $data from intermediate steps
rm -f $output.*.nrm.gz $output.*.nrm.uniq.gz $output.*.langid.gz
#wc -l *.debug.txt



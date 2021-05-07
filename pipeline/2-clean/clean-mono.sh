#!/bin/bash
##
# Basic cleaning of monolingual corpora.
#
# Usage:
#   bash clean-mono.sh prefix_input prefix_output
#

set -x
set -euo pipefail

test -v CLEAN_TOOLS

# assuming monolingual data is always in English
lang=en

mono=$1
output=$2


# Check if files exist
test -s $mono.$lang.gz || exit 1

######################################################################
# Basic preprocessing
pigz -dc $mono.$lang.gz \
    | parallel --no-notice --pipe -k -j16 --block 50M "perl $CLEAN_TOOLS/remove-non-printing-char.perl | perl $CLEAN_TOOLS/normalize-punctuation.perl -l $lang" \
    | pigz > $output.$lang.nrm.gz

test -s $output.$lang.nrm.gz || exit 1

######################################################################
# Deduplication
pigz -dc $output.$lang.nrm.gz | LC_ALL=C sort -S 10G | uniq | pigz > $output.$lang.nrm.uniq.gz

test -s $output.$lang.nrm.uniq.gz || exit 1

######################################################################
# Language identification
pigz -dc $output.$lang.nrm.uniq.gz \
    | parallel --no-notice --pipe -k -j16 --block 50M "python $CLEAN_TOOLS/langid-fasttext.py" \
    | grep -P "^$lang\t" | cut -f2 \
    | pigz > $output.$lang.langid.gz

######################################################################
# Rule-based filtering
pigz -dc $output.$lang.langid.gz \
    | parallel --no-notice --pipe -k -j16 --block 50M "python $CLEAN_TOOLS/clean-mono.py -l $lang --debug" \
    2> $output.$lang.clean.debug.txt \
    | pigz > $output.$lang.clean.gz

test -s $output.$lang.clean.gz || exit 1

# Remove data from intermediate steps
rm -f $output.*.nrm.gz $output.*.nrm.uniq.gz $output.*.langid.gz
#wc -l *.debug.txt



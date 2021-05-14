#!/bin/bash
##
# Basic cleaning of parallel corpora.
#
# Usage:
#   bash clean-corpus.sh prefix_input prefix_output
#

set -x
set -euo pipefail

clean_tools=${CLEAN_TOOLS:-./tools}
export PYTHONPATH=$clean_tools
test -v SRC
test -v TRG

data=$1
output=$2

mkdir -p $(dirname $output)

# Check if files exist
test -s $data.$SRC.gz || exit 1
test -s $data.$TRG.gz || exit 1

echo "CLeaning ${data}"

######################################################################
echo "Basic preprocessing"
for lng in $SRC $TRG; do
    pigz -dc $data.$lng.gz \
        | parallel --no-notice --pipe -k -j$(nproc) --block 50M "perl $clean_tools/remove-non-printing-char.perl | perl $clean_tools/normalize-punctuation.perl -l $lng" \
        | pigz > $output.$lng.nrm.gz
done

test -s $output.$SRC.nrm.gz || exit 1
test -s $output.$TRG.nrm.gz || exit 1

######################################################################
echo "Deduplication"
test -s $output.$SRC$TRG.nrm.uniq.gz || \
paste <(pigz -dc $output.$SRC.nrm.gz) <(pigz -dc $output.$TRG.nrm.gz) \
    | LC_ALL=C sort -S 10G | uniq \
    | pigz > $output.$SRC$TRG.nrm.uniq.gz

test -s $output.$SRC$TRG.nrm.uniq.gz || exit 1

######################################################################
echo "Rule-based filtering"
test -s $output.$SRC$TRG.rule-based.gz || \
pigz -dc $output.$SRC$TRG.nrm.uniq.gz \
    | parallel --no-notice --pipe -k -j$(nproc) --block 50M "python3 $clean_tools/clean_parallel.py -l1 $SRC -l2 $TRG --debug" \
    2> $output.$SRC$TRG.clean.debug.txt \
    | pigz > $output.$SRC$TRG.rule-based.gz

test -s $output.$SRC$TRG.rule-based.gz || exit 1

######################################################################
echo "Language identification"
test -s $output.$SRC$TRG.langid.gz \
pigz -dc $output.$SRC$TRG.rule-based.gz \
    | parallel --no-notice --pipe -k -j$(nproc) --block 50M "python3 -Wi $clean_tools/langid_fasttext.py -f 1 | python3 -Wi $clean_tools/langid_fasttext.py -f 1" \
    | grep -P "^$SRC\t$TRG\t" \
    | cut -f3,4 \
    | pigz > $output.$SRC$TRG.langid.gz

test -s $output.$SRC$TRG.langid.gz

######################################################################
echo "Removing leading and repetitive white spaces"
pigz -dc $output.$SRC$TRG.langid.gz | cut -f1 | sed -e 's/^[[:space:]]*//' | tr -s " " \
    | pigz > $output.$SRC.clean.gz
pigz -dc $output.$SRC$TRG.langid.gz | cut -f2 | sed -e 's/^[[:space:]]*//' | tr -s " " \
    | pigz > $output.$TRG.clean.gz

test -s $output.$SRC.clean.gz || exit 1
test -s $output.$TRG.clean.gz || exit 1

echo "Remove $data from intermediate steps"
rm -f $output.*.nrm.gz $output.*.nrm.uniq.gz $output.*.langid.gz $output.*.rule-based.gz


echo "Clean data is written to  ${output}"



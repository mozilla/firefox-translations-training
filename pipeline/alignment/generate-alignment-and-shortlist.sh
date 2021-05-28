#!/bin/bash -v
##
# Generates alignment and lexical shortlist for a corpus.
#
# Usage:
#   bash generate-alignment-and-shortlist.sh corpus_prefix vocab_path output_dir
#

set -x
set -euo pipefail


test -v MARIAN
test -v BIN
tests -v SRC
test -v TRG

corpus_prefix=$1
vocab_path=$2
dir=$3

test -e $BIN/atools      || exit 1
test -e $BIN/extract_lex || exit 1
test -e $BIN/fast_align  || exit 1

mkdir -p $dir

CORPUS_SRC=$corpus_prefix.SRC.gz
CORPUS_TRG=$corpus_prefix.TRG.gz

# Subword segmentation with SentencePiece.
test -s $dir/corpus.spm.$SRC || cat $CORPUS_SRC | pigz -dc | parallel --no-notice --pipe -k -j$(nproc) --block 50M "$MARIAN/spm_encode --model $vocab_path" > $dir/corpus.spm.$SRC
test -s $dir/corpus.spm.$TRG || cat $CORPUS_TRG | pigz -dc | parallel --no-notice --pipe -k -j$(nproc) --block 50M "$MARIAN/spm_encode --model $vocab_path" > $dir/corpus.spm.$TRG

test -s $dir/corpus     || paste $dir/corpus.spm.$SRC $dir/corpus.spm.$TRG | sed 's/\t/ ||| /' > $dir/corpus

# Alignment.
test -s $dir/align.s2t  || $BIN/fast_align -vod  -i $dir/corpus > $dir/align.s2t
test -s $dir/align.t2s  || $BIN/fast_align -vodr -i $dir/corpus > $dir/align.t2s

test -s $dir/corpus.aln || $BIN/atools -i $dir/align.s2t -j $dir/align.t2s -c grow-diag-final-and > $dir/corpus.aln

# Shortlist.
test -s $dir/lex.s2t    || $BIN/extract_lex $dir/corpus.spm.$TRG $dir/corpus.spm.$SRC $dir/corpus.aln $dir/lex.s2t $dir/lex.t2s

# Clean.
rm $dir/corpus $dir/corpus.spm.?? $dir/align.???

pigz $dir/corpus.aln
pigz $dir/lex.s2t

# Shortlist pruning (optional).
test -e $dir/vocab.txt         || $MARIAN/spm_export_vocab --model=$VOCAB --output=$dir/vocab.txt
test -e $dir/lex.s2t.pruned.gz || pigz -dc $dir/lex.s2t.gz | grep -v NULL | python3 prune_shortlist.py 100 $dir/vocab.txt | pigz > $dir/lex.s2t.pruned.gz


echo "Outputs:"
ll $dir/*.gz


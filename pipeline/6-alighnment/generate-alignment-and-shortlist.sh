#!/bin/bash

set -eo pipefail

# Adjust variables if needed.
MARIAN=../../marian-dev/build
VOCAB=../../esen/enes.teacher.bigx2/vocab.esen.spm
SRC=en
TRG=es
CORPUS_SRC=corpus.$SRC.gz
CORPUS_TRG=corpus.$TRG.gz

BIN=bin
test -e $BIN/atools      || exit 1
test -e $BIN/extract_lex || exit 1
test -e $BIN/fast_align  || exit 1

DIR=align
mkdir -p $DIR

echo $CORPUS_SRC >> $DIR/README
echo $CORPUS_TRG >> $DIR/README

# Subword segmentation with SentencePiece.
test -s $DIR/corpus.spm.$SRC || cat $CORPUS_SRC | pigz -dc | parallel --no-notice --pipe -k -j16 --block 50M "$MARIAN/spm_encode --model $VOCAB" > $DIR/corpus.spm.$SRC
test -s $DIR/corpus.spm.$TRG || cat $CORPUS_TRG | pigz -dc | parallel --no-notice --pipe -k -j16 --block 50M "$MARIAN/spm_encode --model $VOCAB" > $DIR/corpus.spm.$TRG

test -s $DIR/corpus     || paste $DIR/corpus.spm.$SRC $DIR/corpus.spm.$TRG | sed 's/\t/ ||| /' > $DIR/corpus

# Alignment.
test -s $DIR/align.s2t  || $BIN/fast_align -vod  -i $DIR/corpus > $DIR/align.s2t
test -s $DIR/align.t2s  || $BIN/fast_align -vodr -i $DIR/corpus > $DIR/align.t2s

test -s $DIR/corpus.aln || $BIN/atools -i $DIR/align.s2t -j $DIR/align.t2s -c grow-diag-final-and > $DIR/corpus.aln

# Shortlist.
test -s $DIR/lex.s2t    || $BIN/extract_lex $DIR/corpus.spm.$TRG $DIR/corpus.spm.$SRC $DIR/corpus.aln $DIR/lex.s2t $DIR/lex.t2s

# Clean.
rm $DIR/corpus $DIR/corpus.spm.?? $DIR/align.???

pigz $DIR/corpus.aln
pigz $DIR/lex.s2t

# Shortlist pruning (optional).
test -e $DIR/vocab.txt         || $MARIAN/spm_export_vocab --model=$VOCAB --output=$DIR/vocab.txt
test -e $DIR/lex.s2t.pruned.gz || pigz -dc $DIR/lex.s2t.gz | grep -v NULL | python3 prune_shortlist.py 100 $DIR/vocab.txt | pigz > $DIR/lex.s2t.pruned.gz


echo "Outputs:"
ll $DIR/*.gz


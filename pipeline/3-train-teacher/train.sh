#!/bin/bash -v

# Set GPUs.
GPUS="0 1 2 3"
MARIAN=../../../marian-dev/build

SRC=es
TRG=en

# Add symbolic links to the training files.
test -e corpus.$SRC.gz || exit 1    # e.g. ../../data/train.en.gz
test -e corpus.$TRG.gz || exit 1    # e.g. ../../data/train.es.translated.gz
test -e corpus.aln.gz  || exit 1    # e.g. ../../alignment/corpus.aln.gz
test -e lex.s2t.gz     || exit 1    # e.g. ../../alignment/lex.s2t.pruned.gz
test -e vocab.spm      || exit 1    # e.g. ../../data/vocab.spm

# Validation set with original source and target sentences (not distilled).
test -e devset.$SRC || exit 1
test -e devset.$TRG || exit 1

mkdir -p tmp

$MARIAN/marian \
    --model model.npz -c student.tiny11.yml \
    --train-sets corpus.{$SRC,$TRG}.gz -T ./tmp --shuffle-in-ram \
    --guided-alignment corpus.aln.gz \
    --vocabs vocab.spm vocab.spm --dim-vocabs 32000 32000 \
    --max-length 200 \
    --exponential-smoothing \
    --mini-batch-fit -w 12000 --mini-batch 1000 --maxi-batch 1000 --devices $GPUS --sync-sgd --optimizer-delay 2 \
    --learn-rate 0.0003 --lr-report --lr-warmup 16000 --lr-decay-inv-sqrt 32000 \
    --cost-type ce-mean-words \
    --optimizer-params 0.9 0.98 1e-09 --clip-norm 0 \
    --valid-freq 5000 --save-freq 5000 --disp-freq 1000 --disp-first 10 \
    --valid-metrics bleu-detok ce-mean-words \
    --valid-sets devset.{$SRC,$TRG} --valid-translation-output devset.out --quiet-translation \
    --valid-mini-batch 64 --beam-size 1 --normalize 1 \
    --early-stopping 20 \
    --overwrite --keep-best \
    --log train.log --valid-log valid.log

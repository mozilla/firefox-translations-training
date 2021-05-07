#!/bin/bash -v

MARIAN=../../../marian-dev/build

SRC=es
TRG=en

mkdir -p eval

# WMT newstests.
for prefix in wmt12 wmt13; do
    echo "### Evaluating $prefix $SRC-$TRG"
    sacrebleu -t $prefix -l $SRC-$TRG --echo src \
        | tee eval/$prefix.$SRC \
        | $MARIAN/marian-decoder -c model.npz.best-bleu-detok.npz.decoder.yml -w 4000 --quiet --log eval/$prefix.log $@ \
        | tee eval/$prefix.$TRG \
        | sacrebleu -d -t $prefix -l $SRC-$TRG \
        | tee eval/$prefix.$TRG.bleu
done

exit

# Custom test sets.
DATA=../data

for prefix in UNv1.0.testset IWSLT13.TED.tst2013; do
    echo "### Evaluating $prefix $SRC-$TRG"
    cat $DATA/$prefix.$SRC \
        | tee eval/$prefix.$SRC \
        | $MARIAN/marian-decoder -c model.npz.best-bleu-detok.npz.decoder.yml -w 4000 --quiet --log eval/$prefix.log $@ \
        | tee eval/$prefix.$TRG \
        | sacrebleu $DATA/$prefix.$TRG \
        | tee eval/$prefix.$TRG.bleu
done

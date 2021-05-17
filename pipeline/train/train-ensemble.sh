
for i in $(seq 1 $N)
do
  mkdir -p model/ens$i
  # train model
    $MARIAN_TRAIN \
        --model model/ens$i/model.npz --type s2s \
        --train-sets data/all.bpe.en data/all.bpe.de \
        --max-length 100 \
        --vocabs model/vocab.ende.yml model/vocab.ende.yml \
        --mini-batch-fit -w $WORKSPACE --mini-batch 1000 --maxi-batch 1000 \
        --valid-freq 5000 --save-freq 5000 --disp-freq 500 \
        --valid-metrics ce-mean-words perplexity translation \
        --valid-sets data/valid.bpe.en data/valid.bpe.de \
        --valid-script-path "bash ./scripts/validate.sh" \
        --valid-translation-output data/valid.bpe.en.output --quiet-translation \
        --beam-size 12 --normalize=1 \
        --valid-mini-batch 64 \
        --overwrite --keep-best \
        --early-stopping 5 --after-epochs $EPOCHS --cost-type=ce-mean-words \
        --log model/ens$i/train.log --valid-log model/ens$i/valid.log \
        --enc-type bidirectional --enc-depth 1 --enc-cell-depth 4 \
        --dec-depth 1 --dec-cell-base-depth 8 --dec-cell-high-depth 1 \
        --tied-embeddings-all --layer-normalization \
        --dropout-rnn 0.1 --label-smoothing 0.1 \
        --learn-rate 0.0003 --lr-decay-inv-sqrt 16000 --lr-report \
        --optimizer-params 0.9 0.98 1e-09 --clip-norm 5 \
        --devices $GPUS --sync-sgd --seed $i$i$i$i  \
        --exponential-smoothing
done

for i in $(seq 1 $N)
do
  mkdir -p model/ens-rtl$i
  # train model
    $MARIAN_TRAIN \
        --model model/ens-rtl$i/model.npz --type s2s \
        --train-sets data/all.bpe.en data/all.bpe.de \
        --max-length 100 \
        --vocabs model/vocab.ende.yml model/vocab.ende.yml \
        --mini-batch-fit -w $WORKSPACE --mini-batch 1000 --maxi-batch 1000 \
        --valid-freq 5000 --save-freq 5000 --disp-freq 500 \
        --valid-metrics ce-mean-words perplexity translation \
        --valid-sets data/valid.bpe.en data/valid.bpe.de \
        --valid-script-path "bash ./scripts/validate.sh" \
        --valid-translation-output data/valid.bpe.en.output --quiet-translation \
        --beam-size 12 --normalize=1 \
        --valid-mini-batch 64 \
        --overwrite --keep-best \
        --early-stopping 5 --after-epochs $EPOCHS --cost-type=ce-mean-words \
        --log model/ens-rtl$i/train.log --valid-log model/ens-rtl$i/valid.log \
        --enc-type bidirectional --enc-depth 1 --enc-cell-depth 4 \
        --dec-depth 1 --dec-cell-base-depth 8 --dec-cell-high-depth 1 \
        --tied-embeddings-all --layer-normalization \
        --transformer-dropout 0.1 --label-smoothing 0.1 \
        --learn-rate 0.0003 --lr-decay-inv-sqrt 16000 --lr-report \
        --optimizer-params 0.9 0.98 1e-09 --clip-norm 5 \
        --devices $GPUS --sync-sgd --seed $i$i$i$i$i \
        --exponential-smoothing --right-left
done

conda activate bergamot-training-env

python ../marian-tensorboard/tb_log_parser.py --prefix=

tensorboard --logdir=./ --host=0.0.0.0
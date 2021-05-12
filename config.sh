WORKDIR=$(pwd)
CUDA_DIR=/usr/local/cuda-11.0
DATA_DIR=${WORKDIR}/data
MODELS_DIR=${WORKDIR}/models
MARIAN=${WORKDIR}/marian-dev/build
CLEAN_TOOLS=${WORKDIR}/students/train-student/clean/tools
TEACHER_PATH=${MODELS_DIR}/teacher

SRC=ru
TRG=en
TRAIN_DATASETS=OPUS_Europarl_v8
DEVTEST_DATASETS="newstest2013 newstest2012 newstest2011 newstest2010"
TEST_DATASETS="wmt20 wmt18 wmt16 wmt15"
MONO_DATASETS=
MONO_MAX_SENTENCES=200000000


# marian --devices parameter for GPUs to use, for example 0 1 2 3
GPUS=$(seq -s " " 0 $(( $(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l)-1 )))
WORKSPACE=14000
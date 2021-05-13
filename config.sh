WORKDIR=$(pwd)
CUDA_DIR=/usr/local/cuda-11.0
DATA_DIR=${WORKDIR}/data
MODELS_DIR=${WORKDIR}/models
MARIAN=${WORKDIR}/marian-dev/build
CLEAN_TOOLS=${WORKDIR}/students/train-student/clean/tools
TEACHER_PATH=${MODELS_DIR}/teacher

SRC=ru
TRG=en
# parallel corpus
TRAIN_DATASETS="opus_OPUS-ParaCrawl/v7.1"
DEVTEST_DATASETS="mtdata_newstest2019_ruen mtdata_newstest2017_ruen mtdata_newstest2015_ruen mtdata_newstest2014_ruen"
TEST_DATASETS="wmt20 wmt18 wmt16 wmt13"
# mono for source language (ex. paracrawl_paracrawl8  commoncrawl_wmt16)
MONO_DATASETS="news-crawl_news.2020"
MONO_MAX_SENTENCES=100000000


# marian --devices parameter for GPUs to use, for example 0 1 2 3
GPUS=$(seq -s " " 0 $(( $(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l)-1 )))
WORKSPACE=14000
#!/bin/bash
##
# Pipeline config
#
# Usage:
#   source ./config.sh
#

# Export all vairables
set -a

WORKDIR=$(pwd)
CUDA_DIR=/usr/local/cuda-11.2
DATA_DIR=${DATA_DIR:-${WORKDIR}/data}
MODELS_DIR=${MODELS_DIR:-${WORKDIR}/models}
MARIAN=${MARIAN:-${WORKDIR}/3rd_party/marian-dev/build}
CLEAN_TOOLS=${WORKDIR}/pipeline/clean/tools
BIN=${WORKDIR}/bin
TMP=/tmp

EXPERIMENT=test
SRC=ru
TRG=en

# parallel corpus
TRAIN_DATASETS="opus_OPUS-ParaCrawl/v7.1"
DEVTEST_DATASETS="mtdata_newstest2019_ruen mtdata_newstest2017_ruen mtdata_newstest2015_ruen mtdata_newstest2014_ruen"
# sacrebleu
TEST_DATASETS="wmt20 wmt18 wmt16 wmt13"
# monolingual datasets (ex. paracrawl-mono_paracrawl8, commoncrawl_wmt16, news-crawl_news.2020)
# to be translated by the teacher model
MONO_DATASETS_SRC="news-crawl_news.2020 news-crawl_news.2019 news-crawl_news.2018 news-crawl_news.2017 "\
"news-crawl_news.2016 news-crawl_news.2015 news-crawl_news.2014 news-crawl_news.2013 news-crawl_news.2012 "\
"news-crawl_news.2011"
# to be translated by the shallow s2s model to augment teacher corpus with back-translations
# leave empty to skip augmentation step (high resource languages)
MONO_DATASETS_TRG="news-crawl_news.2020"
# limits per downloaded dataset
MONO_MAX_SENTENCES_SRC=100000000
MONO_MAX_SENTENCES_TRG=20000000


# marian --devices parameter for GPUs to use, for example 0 1 2 3
GPUS=$(seq -s " " 0 $(( $(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l)-1 )))
# for 12 GB GPU
WORKSPACE=9000

set +a
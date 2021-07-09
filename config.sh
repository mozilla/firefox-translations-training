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
CONDA_DIR=${HOME}/miniconda3
TMP=/tmp

EXPERIMENT=test
SRC=ru
TRG=en

# parallel corpus
TRAIN_DATASETS="opus_OPUS-ada83/v1 opus_OPUS-PHP/v1 opus_OPUS-Wikipedia/v1.0 "\
"opus_OPUS-ParaCrawl/v8 opus_OPUS-News-Commentary/v16 opus_OPUS-TED2013/v1.1 opus_OPUS-EUbookshop/v2 "\
"opus_OPUS-TED2020/v1 opus_OPUS-Books/v1 opus_OPUS-TildeMODEL/v2018 opus_OPUS-UNPC/v1.0 "\
"opus_OPUS-Tanzil/v1 opus_OPUS-ELRC_2922/v1 opus_OPUS-infopankki/v1 opus_OPUS-XLEnt/v1.1 "\
"opus_OPUS-WikiMatrix/v1 opus_OPUS-GlobalVoices/v2018q4 opus_OPUS-QED/v2.0a "\
"opus_OPUS-tico-19/v2020-10-28 opus_OPUS-UN/v20090831 opus_OPUS-wikimedia/v20210402 "\
"opus_OPUS-WMT-News/v2019 opus_OPUS-Tatoeba/v2021-03-10 mtdata_JW300"
DEVTEST_DATASETS="mtdata_newstest2019_ruen mtdata_newstest2017_ruen mtdata_newstest2015_ruen mtdata_newstest2014_ruen"
# sacrebleu
TEST_DATASETS="sacrebleu_wmt20 sacrebleu_wmt18 sacrebleu_wmt16 sacrebleu_wmt13"
# monolingual datasets (ex. paracrawl-mono_paracrawl8, commoncrawl_wmt16, news-crawl_news.2020)
# to be translated by the teacher model
MONO_DATASETS_SRC="news-crawl_news.2020 news-crawl_news.2019 news-crawl_news.2018 news-crawl_news.2017 "\
"news-crawl_news.2016 news-crawl_news.2015 news-crawl_news.2014 news-crawl_news.2013 news-crawl_news.2012 "\
"news-crawl_news.2011"
# to be translated by the shallow s2s model to augment teacher corpus with back-translations
# leave empty to skip augmentation step (high resource languages)
MONO_DATASETS_TRG=""
# limits per downloaded dataset
MONO_MAX_SENTENCES_SRC=100000000
MONO_MAX_SENTENCES_TRG=20000000
BICLEANER_THRESHOLD=0.5


# marian --devices parameter for GPUs to use, for example 0 1 2 3
GPUS=$(seq -s " " 0 $(( $(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l)-1 )))
# for 12 GB GPU
WORKSPACE=9000

set +a
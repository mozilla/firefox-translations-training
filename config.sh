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
TRAIN_DATASETS="opus_ada83/v1 opus_UN/v20090831 opus_GNOME/v1 opus_wikimedia/v20210402 opus_CCMatrix/v1 opus_Wikipedia/v1.0 opus_tico-19/v2020-10-28 opus_KDE4/v2 opus_OpenSubtitles/v2018 opus_MultiUN/v1 opus_GlobalVoices/v2018q4 opus_ELRC_2922/v1 opus_PHP/v1 opus_Tatoeba/v2021-03-10 opus_Tanzil/v1 opus_XLEnt/v1.1 opus_TildeMODEL/v2018 opus_Ubuntu/v14.10 opus_TED2013/v1.1 opus_infopankki/v1 opus_EUbookshop/v2 opus_ParaCrawl/v8 opus_Books/v1 opus_WMT-News/v2019 opus_bible-uedin/v1 opus_WikiMatrix/v1 opus_QED/v2.0a opus_CCAligned/v1 opus_TED2020/v1 opus_News-Commentary/v16 opus_UNPC/v1.0"\
" mtdata_cc_aligned mtdata_airbaltic mtdata_GlobalVoices_2018Q4 mtdata_UNv1_test mtdata_neulab_tedtalksv1_train mtdata_neulab_tedtalksv1_dev mtdata_wmt13_commoncrawl mtdata_czechtourism mtdata_paracrawl_bonus mtdata_worldbank mtdata_wiki_titles_v1 mtdata_WikiMatrix_v1 mtdata_wmt18_news_commentary_v13 mtdata_wiki_titles_v2 mtdata_news_commentary_v14 mtdata_UNv1_dev mtdata_neulab_tedtalksv1_test mtdata_JW300"
DEVTEST_DATASETS="flores_dev mtdata_newstest2019_ruen mtdata_newstest2017_ruen mtdata_newstest2015_ruen mtdata_newstest2014_ruen"
TEST_DATASETS="flores_devtest sacrebleu_wmt20 sacrebleu_wmt18 sacrebleu_wmt16 sacrebleu_wmt13"
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
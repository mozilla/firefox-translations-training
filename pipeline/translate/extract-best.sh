#!/bin/bash
##
# Extracts best translations using n-best lists and reference translations
#

set -x
set -euo pipefail

dir=$1
threads=$2
files=$3

echo $files |
  parallel --no-notice -k -j "${threads}" \
    "test -e ${dir}/{}.nbest.out || \
    python pipeline/translate/bestbleu.py -i ${dir}/{}.nbest -r ${dir}/{}.ref -m bleu > ${dir}/{}.nbest.out"

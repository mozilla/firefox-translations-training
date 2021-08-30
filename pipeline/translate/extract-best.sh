#!/bin/bash
##
# Extracts best translations using n-best lists and reference translations
#

set -x
set -euo pipefail

dir=$1
files=$2

#find "${dir}" -regex '.*file\.[0-9]+' -printf "%f\n" |
echo $files |
  parallel --no-notice -k -j "$(nproc)" \
    "test -e ${dir}/{}.nbest.out || \
    python pipeline/translate/bestbleu.py -i ${dir}/{}.nbest -r ${dir}/{}.ref -m bleu > ${dir}/{}.nbest.out"

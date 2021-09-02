#!/bin/bash
##
# Extracts best translations using n-best lists and reference translations
#

set -x
set -euo pipefail

threads=$1
files=( "${@:2}" )


parallel --no-notice -k -j "${threads}" \
  "test -e {}.nbest.out || \
  python pipeline/translate/bestbleu.py -i {}.nbest -r {}.ref -m bleu > {}.nbest.out" ::: "${files[@]}"

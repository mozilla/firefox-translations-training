#!/bin/bash
##
# Basic cleaning of monolingual corpora.
#
# Usage:
#   bash clean-mono.sh lang prefix_input prefix_output
#

set -x
set -euo pipefail

echo "###### Cleaning monolingual data"

lang=$1
input=$2
output=$3
threads=$4

test -v CLEAN_TOOLS

echo "### CLeaning ${input}"

dir="$(dirname "${output}")"
tmp="${dir}/tmp"
mkdir -p "${tmp}"

######################################################################
echo "### Basic preprocessing"
test -s "${output}.${lang}.nrm.gz" ||
  pigz -dc "${input}.${lang}.gz" |
  parallel --no-notice --pipe -k -j "${threads}" --block 50M \
    "perl ${CLEAN_TOOLS}/remove-non-printing-char.perl | perl ${CLEAN_TOOLS}/normalize-punctuation.perl -l ${lang}" |
  pigz >"${output}.${lang}.nrm.gz"

######################################################################
echo "### Deduplication"
test -s "${output}.${lang}.nrm.uniq.gz" ||
  pigz -dc "${output}.${lang}.nrm.gz" |
  LC_ALL=C sort -S 10G -T "${tmp}" |
  uniq |
  pigz >"${output}.${lang}.nrm.uniq.gz"

######################################################################
echo "### Language identification"
test -s "${output}.${lang}.langid.gz" ||
  pigz -dc "${output}.${lang}.nrm.uniq.gz" |
  # memory intensive
  parallel --no-notice --pipe -k -j "$(echo "${threads}"/4 | bc)" --block 50M "python ${CLEAN_TOOLS}/langid_fasttext.py" |
  grep -P "^${lang}\t" | cut -f2 |
  pigz >"${output}.${lang}.langid.gz"

######################################################################
echo "### Rule-based filtering"

pigz -dc "${output}.${lang}.langid.gz" |
parallel --no-notice --pipe -k -j "${threads}" --block 50M \
  "python ${CLEAN_TOOLS}/clean_mono.py -l ${lang} --debug" \
  2>"${output}.${lang}.clean.debug.txt" |
pigz >"${output}.${lang}.gz"

test -s "${output}.${lang}.gz" || exit 1

echo "### Remove data from intermediate steps"
rm -rf "${output}".*.nrm.gz "${output}".*.nrm.uniq.gz "${output}".*.langid.gz "${tmp}"

echo "### Clean data is written to  ${output}"

echo "###### Done: Cleaning monolingual data"

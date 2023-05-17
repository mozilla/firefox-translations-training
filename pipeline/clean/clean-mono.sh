#!/bin/bash
##
# Basic cleaning of monolingual corpora.
#

set -x
set -euo pipefail

echo "###### Cleaning monolingual data"

lang=$1
input_prefix=$2
output_prefix=$3
threads=$4
dataset=$5

echo "### Cleaning ${input_prefix}"

cd "$(dirname "${0}")"
export PYTHONPATH="tools"

dir="$(dirname "${output_prefix}")"
mkdir -p "${dir}"

######################################################################
echo "### Basic preprocessing"
test -s "${output_prefix}.${lang}.nrm.gz" ||
  pigz -dc "${input_prefix}.${lang}.gz" |
  parallel --no-notice --pipe -k -j "${threads}" --block 50M \
    "perl tools/deescape-special-chars.perl | perl tools/remove-non-printing-char.perl" |
  pigz >"${output_prefix}.${lang}.nrm.gz"

#####################################################################
echo "### Apply monolingual fixes"
if [[ ! -x fixes/${dataset}.${lang}.sh ]]; then
  test -s "${output_prefix}.${lang}.monofix.gz" ||
    cp "${output_prefix}.${lang}.nrm.gz" "${output_prefix}.${lang}.monofix.gz"
else
  test -s "${output_prefix}.${lang}.monofix.gz" ||
    pigz -dc "${output_prefix}.${lang}.nrm.gz" \
        | fixes/"${dataset}"."${lang}".sh \
        | pigz >"${output_prefix}.${lang}.monofix.gz"
fi

######################################################################
echo "### Language identification"
test -s "${output_prefix}.${lang}.langid.gz" ||
  pigz -dc "${output_prefix}.${lang}.monofix.gz" |
  # memory intensive
  parallel --no-notice --pipe -k -j "$(echo "${threads}"/4 | bc)" --block 50M "python tools/langid_fasttext.py" |
  grep -P "^${lang}\t" | cut -f2 |
  pigz >"${output_prefix}.${lang}.langid.gz"

######################################################################

echo "### Rule-based filtering"

pigz -dc "${output_prefix}.${lang}.langid.gz" |
parallel --no-notice --pipe -k -j "${threads}" --block 50M \
  "python tools/clean_mono.py -l ${lang} --debug" \
  2>"${output_prefix}.${lang}.clean.debug.txt" |
pigz >"${output_prefix}.${lang}.gz"

test -s "${output_prefix}.${lang}.gz" || exit 1

echo "### Remove data from intermediate steps"
rm -rf "${output_prefix}".*.nrm.gz "${output_prefix}".*.langid.gz \
  "${output_prefix}".*.monofix.gz

echo "### Clean data is written to  ${output_prefix}"

echo "###### Done: Cleaning monolingual data"

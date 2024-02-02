#!/bin/bash
##
# Basic cleaning of monolingual corpora.
# cache bust
#
# This script takes in a an archive file, e.g. /builds/worker/artifacts/news_2007.en.zst
# and rewrites in place using a variety of cleaning rules including:
#
#  - De-escape special characters.
#  - Remove non-printing characters.
#  - Specific dataset fixes provided by: pipeline/clean/fixes/*.sh
#  - Filter by language detection (via fastText)

set -x
set -euo pipefail

echo "###### Cleaning monolingual data"

#                   Example inputs:
lang=$1             # en
input_prefix=$2     # $MOZ_FETCHES_DIR/news_2007
output_prefix=$3    # /builds/worker/artifacts/news_2007
threads=$4          # auto
dataset=$5          # news-crawl_news.2007

# Example output: /builds/worker/artifacts/news_2007.en.zst

COMPRESSION_CMD="${COMPRESSION_CMD:-pigz}"
ARTIFACT_EXT="${ARTIFACT_EXT:-gz}"

echo "### Cleaning ${input_prefix}"

if [ "$threads" = "auto" ]; then
  threads=$(nproc)
fi
cd "$(dirname "${0}")"
export PYTHONPATH="tools"

dir="$(dirname "${output_prefix}")"
mkdir -p "${dir}"

######################################################################
echo "### Basic preprocessing from moses"
test -s "${output_prefix}.${lang}.nrm.${ARTIFACT_EXT}" ||
  ${COMPRESSION_CMD} -dc "${input_prefix}.${lang}.${ARTIFACT_EXT}" |
  parallel --no-notice --pipe -k -j "${threads}" --block 50M \
    "perl tools/deescape-special-chars.perl | perl tools/remove-non-printing-char.perl" |
  ${COMPRESSION_CMD} -c >"${output_prefix}.${lang}.nrm.${ARTIFACT_EXT}"

#####################################################################
echo "### Apply dataset fixes from pipeline/clean/fixes"
if [[ ! -x fixes/${dataset}.${lang}.sh ]]; then
  test -s "${output_prefix}.${lang}.monofix.${ARTIFACT_EXT}" ||
    cp "${output_prefix}.${lang}.nrm.${ARTIFACT_EXT}" "${output_prefix}.${lang}.monofix.${ARTIFACT_EXT}"
else
  test -s "${output_prefix}.${lang}.monofix.${ARTIFACT_EXT}" ||
    ${COMPRESSION_CMD} -dc "${output_prefix}.${lang}.nrm.${ARTIFACT_EXT}" \
        | fixes/"${dataset}"."${lang}".sh \
        | ${COMPRESSION_CMD} >"${output_prefix}.${lang}.monofix.${ARTIFACT_EXT}"
fi

######################################################################
echo "### Filter by language identification"
test -s "${output_prefix}.${lang}.langid.${ARTIFACT_EXT}" ||
  # langid_fasttext.py will download this file if it is not already present. When it runs in
  # parallel, this will typically cause the file to be corrupt.
  test -s tools/lid.176.bin || wget -O tools/lid.176.bin https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin
  ${COMPRESSION_CMD} -dc "${output_prefix}.${lang}.monofix.${ARTIFACT_EXT}" |
  # memory intensive
  parallel --no-notice --pipe -k -j "$(echo "${threads}"/4 | bc)" --block 50M "python3 tools/langid_fasttext.py" |
  grep -P "^${lang}\t" | cut -f2 |
  ${COMPRESSION_CMD} >"${output_prefix}.${lang}.langid.${ARTIFACT_EXT}"

######################################################################
echo "### Rule-based filtering"

${COMPRESSION_CMD} -dc "${output_prefix}.${lang}.langid.${ARTIFACT_EXT}" |
parallel --no-notice --pipe -k -j "${threads}" --block 50M \
  "python3 tools/clean_mono.py -l ${lang} --debug" \
  2>"${output_prefix}.${lang}.clean.debug.txt" |
${COMPRESSION_CMD} >"${output_prefix}.${lang}.${ARTIFACT_EXT}"

test -s "${output_prefix}.${lang}.${ARTIFACT_EXT}" || exit 1

######################################################################
echo "### Remove data from intermediate steps"
rm -rf "${output_prefix}".*.nrm.${ARTIFACT_EXT} "${output_prefix}".*.langid.${ARTIFACT_EXT} \
  "${output_prefix}".*.monofix.${ARTIFACT_EXT}

echo "### Rule-based cleaning log written to: ${output_prefix}.${lang}.clean.debug.txt"
echo "### Clean data is written to: ${output_prefix}.${lang}.${ARTIFACT_EXT}"

echo "###### Done: Cleaning monolingual data"

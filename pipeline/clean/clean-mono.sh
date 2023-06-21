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
echo "### Basic preprocessing"
test -s "${output_prefix}.${lang}.nrm.${ARTIFACT_EXT}" ||
  ${COMPRESSION_CMD} -dc "${input_prefix}.${lang}.${ARTIFACT_EXT}" |
  parallel --no-notice --pipe -k -j "${threads}" --block 50M \
    "perl tools/deescape-special-chars.perl | perl tools/remove-non-printing-char.perl" |
  ${COMPRESSION_CMD} -c >"${output_prefix}.${lang}.nrm.${ARTIFACT_EXT}"

#####################################################################
echo "### Apply monolingual fixes"
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
echo "### Language identification"
test -s "${output_prefix}.${lang}.langid.${ARTIFACT_EXT}" ||
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

echo "### Remove data from intermediate steps"
rm -rf "${output_prefix}".*.nrm.${ARTIFACT_EXT} "${output_prefix}".*.langid.${ARTIFACT_EXT} \
  "${output_prefix}".*.monofix.${ARTIFACT_EXT}

echo "### Clean data is written to  ${output_prefix}"

echo "###### Done: Cleaning monolingual data"

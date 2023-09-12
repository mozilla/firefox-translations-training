#!/bin/bash
##
# Basic cleaning of parallel corpora.
#

set -x
set -euo pipefail

echo "###### Cleaning corpus"


test -v SRC
test -v TRG

input_prefix=$1
output_prefix=$2
threads=$3
dataset=$4

COMPRESSION_CMD="${COMPRESSION_CMD:-pigz}"
ARTIFACT_EXT="${ARTIFACT_EXT:-gz}"

if [ "$threads" = "auto" ]; then
  threads=$(nproc)
fi
cd "$(dirname "${0}")"
export PYTHONPATH="tools"

dir="$(dirname "${output_prefix}")"
mkdir -p "${dir}"

echo "### Cleaning ${input_prefix}"

######################################################################
echo "### Basic preprocessing"
for lng in "${SRC}" "${TRG}"; do
  test -s "${output_prefix}.${lng}.nrm.${ARTIFACT_EXT}" ||
    ${COMPRESSION_CMD} -dc "${input_prefix}.${lng}.${ARTIFACT_EXT}" |
    parallel --no-notice --pipe -k -j "${threads}" --block 50M \
      "perl tools/deescape-special-chars.perl | perl tools/remove-non-printing-char.perl" |
    ${COMPRESSION_CMD} >"${output_prefix}.${lng}.nrm.${ARTIFACT_EXT}"
done

#####################################################################
echo "### Apply monolingual fixes"
for lng in $SRC $TRG; do
    if [[ ! -x fixes/${dataset}.${lng}.sh ]]; then
      test -s "${output_prefix}.${lng}.monofix.${ARTIFACT_EXT}" ||
        cp "${output_prefix}.${lng}.nrm.${ARTIFACT_EXT}" "${output_prefix}.${lng}.monofix.${ARTIFACT_EXT}"
    else
        test -s "${output_prefix}.${lng}.monofix.${ARTIFACT_EXT}" ||
          ${COMPRESSION_CMD} -dc "${output_prefix}.${lng}.nrm.${ARTIFACT_EXT}" \
              | fixes/"${dataset}"."${lng}".sh \
              | ${COMPRESSION_CMD} >"${output_prefix}.${lng}.monofix.${ARTIFACT_EXT}"
    fi
done

######################################################################
echo "### Apply bilingual fixes"
if [[ -x fixes/${dataset}.sh ]]; then
    FIX="fixes/${dataset}.sh ${SRC} ${TRG} ${threads}"
else
    FIX="cat"
fi
test -s "${output_prefix}.${SRC}${TRG}.fix.${ARTIFACT_EXT}" ||
  paste <(${COMPRESSION_CMD} -dc "${output_prefix}.${SRC}.monofix.${ARTIFACT_EXT}") <(${COMPRESSION_CMD} -dc "${output_prefix}.${TRG}.monofix.${ARTIFACT_EXT}") \
      | $FIX \
      | ${COMPRESSION_CMD} > "${output_prefix}.${SRC}${TRG}.fix.${ARTIFACT_EXT}"

######################################################################
echo "### Rule-based filtering"
test -s "${output_prefix}.${SRC}${TRG}.rule-based.${ARTIFACT_EXT}" ||
  ${COMPRESSION_CMD} -dc "${output_prefix}.${SRC}${TRG}.fix.${ARTIFACT_EXT}" |
  parallel --no-notice --pipe -k -j "${threads}" --block 50M \
    "python3 tools/clean_parallel.py -l1 ${SRC} -l2 ${TRG} --debug" \
    2>"${output_prefix}.${SRC}${TRG}.clean.debug.txt" |
  ${COMPRESSION_CMD} >"${output_prefix}.${SRC}${TRG}.rule-based.${ARTIFACT_EXT}"

######################################################################
echo "### Language identification"
test -s "${output_prefix}.${SRC}${TRG}.langid.${ARTIFACT_EXT}" ||
  # langid_fasttext.py will download this file if it is not already present. When it runs in
  # parallel, this will typically cause the file to be corrupt.
  test -s tools/lid.176.bin || wget -O tools/lid.176.bin https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin
  ${COMPRESSION_CMD} -dc "${output_prefix}.${SRC}${TRG}.rule-based.${ARTIFACT_EXT}" |
  # memory intensive
  parallel --no-notice --pipe -k -j "$(echo "${threads}"/4 | bc)" --block 50M \
    "python3 -Wi tools/langid_fasttext.py -f 1 | python3 -Wi tools/langid_fasttext.py -f 1" |
  grep -P "^${SRC}\t${TRG}\t" |
  cut -f3,4 |
  ${COMPRESSION_CMD} >"${output_prefix}.${SRC}${TRG}.langid.${ARTIFACT_EXT}"

######################################################################
echo "### Removing leading and repetitive white spaces"

${COMPRESSION_CMD} -dc "${output_prefix}.${SRC}${TRG}.langid.${ARTIFACT_EXT}" |
cut -f1 |
sed -e 's/^[[:space:]]*//' |
tr -s " " |
${COMPRESSION_CMD} >"${output_prefix}.${SRC}.${ARTIFACT_EXT}"

${COMPRESSION_CMD} -dc "${output_prefix}.${SRC}${TRG}.langid.${ARTIFACT_EXT}" |
cut -f2 |
sed -e 's/^[[:space:]]*//' |
tr -s " " |
${COMPRESSION_CMD} >"${output_prefix}.${TRG}.${ARTIFACT_EXT}"

test -s "${output_prefix}.${SRC}.${ARTIFACT_EXT}" || exit 1
test -s "${output_prefix}.${TRG}.${ARTIFACT_EXT}" || exit 1

echo "### Remove input_prefix from intermediate steps"
rm -rf "${output_prefix}".*.nrm.${ARTIFACT_EXT} "${output_prefix}".*.langid.${ARTIFACT_EXT} \
  "${output_prefix}".*.rule-based.${ARTIFACT_EXT} "${output_prefix}".*.*fix.${ARTIFACT_EXT}

echo "### Clean ${input_prefix} is written to  ${output_prefix}"

echo "###### Done: Cleaning corpus"

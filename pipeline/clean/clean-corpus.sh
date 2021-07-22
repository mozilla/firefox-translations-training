#!/bin/bash
##
# Basic cleaning of parallel corpora.
#
# Usage:
#   bash clean-corpus.sh prefix_input prefix_output
#

set -x
set -euo pipefail

echo "###### Cleaning corpus"

export PYTHONPATH="${CLEAN_TOOLS}"
test -v SRC
test -v TRG
test -v CLEAN_TOOLS

data=$1
output=$2

dir="$(dirname "${output}")"
tmp="${dir}/tmp"
mkdir -p "${tmp}"

# Check if files exist
test -s "${data}.${SRC}.gz" || exit 1
test -s "${data}.${TRG}.gz" || exit 1

source "${WORKDIR}/pipeline/setup/activate-python.sh"

echo "### CLeaning ${data}"

######################################################################
echo "### Basic preprocessing"
for lng in "${SRC}" "${TRG}"; do
  test -s "${output}.${SRC}.gz" || test -s "${output}.${lng}.nrm.gz" ||
    pigz -dc "${data}.${lng}.gz" |
    parallel --no-notice --pipe -k -j "$(nproc)" --block 50M \
      "perl ${CLEAN_TOOLS}/remove-non-printing-char.perl | perl ${CLEAN_TOOLS}/normalize-punctuation.perl -l ${lng}" |
    pigz >"${output}.${lng}.nrm.gz"
done

######################################################################
echo "### Deduplication"
test -s "${output}.${SRC}.gz" || test -s "${output}.${SRC}${TRG}.nrm.uniq.gz" ||
  paste <(pigz -dc "${output}.${SRC}.nrm.gz") <(pigz -dc "${output}.${TRG}.nrm.gz") |
  LC_ALL=C sort -S 10G -T "${tmp}" |
  uniq |
  pigz >"${output}.${SRC}${TRG}.nrm.uniq.gz"

######################################################################
echo "### Rule-based filtering"
test -s "${output}.${SRC}.gz" || test -s "${output}.${SRC}${TRG}.rule-based.gz" ||
  pigz -dc "${output}.${SRC}${TRG}.nrm.uniq.gz" |
  parallel --no-notice --pipe -k -j "$(nproc)" --block 50M \
    "python3 ${CLEAN_TOOLS}/clean_parallel.py -l1 ${SRC} -l2 ${TRG} --debug" \
    2>"${output}.${SRC}${TRG}.clean.debug.txt" |
  pigz >"${output}.${SRC}${TRG}.rule-based.gz"

######################################################################
echo "### Language identification"
test -s "${output}.${SRC}.gz" || test -s "${output}.${SRC}${TRG}.langid.gz" ||
  pigz -dc "${output}.${SRC}${TRG}.rule-based.gz" |
  # memory intensive
  parallel --no-notice --pipe -k -j "$(echo "$(nproc)"/4 | bc)" --block 50M \
    "python3 -Wi ${CLEAN_TOOLS}/langid_fasttext.py -f 1 | python3 -Wi ${CLEAN_TOOLS}/langid_fasttext.py -f 1" |
  grep -P "^${SRC}\t${TRG}\t" |
  cut -f3,4 |
  pigz >"${output}.${SRC}${TRG}.langid.gz"

######################################################################
echo "### Removing leading and repetitive white spaces"
test -s "${output}.${SRC}.gz" ||
  pigz -dc "${output}.${SRC}${TRG}.langid.gz" |
  cut -f1 |
  sed -e 's/^[[:space:]]*//' |
  tr -s " " |
  pigz >"${output}.${SRC}.gz"
test -s "${output}.${TRG}.gz" ||
  pigz -dc "${output}.${SRC}${TRG}.langid.gz" |
  cut -f2 |
  sed -e 's/^[[:space:]]*//' |
  tr -s " " |
  pigz >"${output}.${TRG}.gz"

test -s "${output}.${SRC}.gz" || exit 1
test -s "${output}.${TRG}.gz" || exit 1

echo "### Remove ${data} from intermediate steps"
rm -f "${output}".*.nrm.gz "${output}".*.nrm.uniq.gz "${output}".*.langid.gz "${output}".*.rule-based.gz
rm -rf "${tmp}"

echo "### Clean data is written to  ${output}"

echo "###### Done: Cleaning corpus"

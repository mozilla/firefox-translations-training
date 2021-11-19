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

cd "$(dirname "${0}")"
export PYTHONPATH="tools"

dir="$(dirname "${output_prefix}")"
tmp="${dir}/tmp"
mkdir -p "${tmp}"

echo "### CLeaning ${input_prefix}"

######################################################################
echo "### Basic preprocessing"
for lng in "${SRC}" "${TRG}"; do
  test -s "${output_prefix}.${lng}.nrm.gz" ||
    pigz -dc "${input_prefix}.${lng}.gz" |
    parallel --no-notice --pipe -k -j "${threads}" --block 50M \
      "perl tools/remove-non-printing-char.perl" |
    pigz >"${output_prefix}.${lng}.nrm.gz"
done

#####################################################################
echo "### Apply monolingual fixes"
for lng in $SRC $TRG; do
    if [[ ! -x fixes/${dataset}.${lng}.sh ]]; then
      test -s "${output_prefix}.${lng}.monofix.gz" ||
        cp "${output_prefix}.${lng}.nrm.gz" "${output_prefix}.${lng}.monofix.gz"
    else
        test -s "${output_prefix}.${lng}.monofix.gz" ||
          pigz -dc "${output_prefix}.${lng}.nrm.gz" \
              | fixes/"${dataset}"."${lng}".sh \
              | pigz >"${output_prefix}.${lng}.monofix.gz"
    fi
done

######################################################################
echo "### Apply bilingual fixes"
if [[ -x fixes/${dataset}.sh ]]; then
    FIX="fixes/${dataset}.sh ${SRC} ${TRG}"
else
    FIX="cat"
fi
test -s "${output_prefix}.${SRC}${TRG}.fix.gz" ||
  paste <(pigz -dc "${output_prefix}.${SRC}.monofix.gz") <(pigz -dc "${output_prefix}.${TRG}.monofix.gz") \
      | $FIX \
      | pigz > "${output_prefix}.${SRC}${TRG}.fix.gz"

######################################################################
echo "### Deduplication"
test -s "${output_prefix}.${SRC}${TRG}.nrm.uniq.gz" ||
  pigz -dc "${output_prefix}.${SRC}${TRG}.fix.gz" |
  LC_ALL=C sort -S 10G -T "${tmp}" |
  uniq |
  pigz >"${output_prefix}.${SRC}${TRG}.nrm.uniq.gz"

######################################################################
echo "### Rule-based filtering"
test -s "${output_prefix}.${SRC}${TRG}.rule-based.gz" ||
  pigz -dc "${output_prefix}.${SRC}${TRG}.nrm.uniq.gz" |
  parallel --no-notice --pipe -k -j "${threads}" --block 50M \
    "python3 tools/clean_parallel.py -l1 ${SRC} -l2 ${TRG} --debug" \
    2>"${output_prefix}.${SRC}${TRG}.clean.debug.txt" |
  pigz >"${output_prefix}.${SRC}${TRG}.rule-based.gz"

######################################################################
echo "### Language identification"
test -s "${output_prefix}.${SRC}${TRG}.langid.gz" ||
  pigz -dc "${output_prefix}.${SRC}${TRG}.rule-based.gz" |
  # memory intensive
  parallel --no-notice --pipe -k -j "$(echo "${threads}"/4 | bc)" --block 50M \
    "python3 -Wi tools/langid_fasttext.py -f 1 | python3 -Wi tools/langid_fasttext.py -f 1" |
  grep -P "^${SRC}\t${TRG}\t" |
  cut -f3,4 |
  pigz >"${output_prefix}.${SRC}${TRG}.langid.gz"

######################################################################
echo "### Removing leading and repetitive white spaces"

pigz -dc "${output_prefix}.${SRC}${TRG}.langid.gz" |
cut -f1 |
sed -e 's/^[[:space:]]*//' |
tr -s " " |
pigz >"${output_prefix}.${SRC}.gz"

pigz -dc "${output_prefix}.${SRC}${TRG}.langid.gz" |
cut -f2 |
sed -e 's/^[[:space:]]*//' |
tr -s " " |
pigz >"${output_prefix}.${TRG}.gz"

test -s "${output_prefix}.${SRC}.gz" || exit 1
test -s "${output_prefix}.${TRG}.gz" || exit 1

echo "### Remove input_prefix from intermediate steps"
rm -f "${output_prefix}".*.nrm.gz "${output_prefix}".*.nrm.uniq.gz "${output_prefix}".*.langid.gz "${output_prefix}".*.rule-based.gz
rm -rf "${tmp}"

echo "### Clean input_prefix is written to  ${output_prefix}"

echo "###### Done: Cleaning corpus"

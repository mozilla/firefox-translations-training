#!/bin/bash
##
# Deduplicates parallel datasets
#

set -x
set -euo pipefail

test -v SRC
test -v TRG

output_prefix=$1
input_prefix=$2

tmp="${output_prefix}/dedup"
mkdir -p "${tmp}"

echo "### Deduplicating ${input_prefix}"
paste <(pigz -dc "${input_prefix}.${SRC}.gz") <(pigz -dc "${input_prefix}.${TRG}.gz") |
LC_ALL=C sort -S 10G -T "${tmp}" |
uniq |
pigz >"${tmp}/dedup-corpus.${SRC}${TRG}.gz"

pigz -dc "${tmp}/dedup-corpus.${SRC}${TRG}.gz" | cut -f1 | pigz > "${output_prefix}.${SRC}.gz"
pigz -dc "${tmp}/dedup-corpus.${SRC}${TRG}.gz" | cut -f2 | pigz > "${output_prefix}.${TRG}.gz"

rm -rf "${tmp}"

echo "###### Done: Deduplicated ${input_prefix} saved into ${output_prefix}"

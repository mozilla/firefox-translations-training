#!/bin/bash
##
# Merges and deduplicates parallel datasets
#

set -x
set -euo pipefail

echo "###### Merging parallel datasets"

test -v SRC
test -v TRG

output_prefix=$1
input_prefixes=( "${@:2}" )

echo "### Merging (each corpus deduplicated separately)"
cat "${input_prefixes[@]/%/.${SRC}.gz}" > "${output_prefix}.${SRC}.gz"
cat "${input_prefixes[@]/%/.${TRG}.gz}" > "${output_prefix}.${TRG}.gz"

echo "###### Done: Merging parallel datasets (separate deduplication)"

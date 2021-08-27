#!/bin/bash
##
# Splits a parallel dataset
#

set -x
set -euo pipefail

corpus_src=$1
corpus_trg=$2
output_dir=$3
chunks=$4

mkdir -p "${output_dir}"
part_len=$(($(pigz -dc "${corpus_src}" | wc -l) / ${chunks} + 1))
pigz -dc "${corpus_src}" |  split -d -l $part_len - "${output_dir}/file."
pigz -dc "${corpus_trg}" |  split -d -l $part_len - "${output_dir}/file." --additional-suffix .ref
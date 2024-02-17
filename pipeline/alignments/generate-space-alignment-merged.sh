#!/bin/bash
##
# Generates space tokenized alignments jointly on original and backtranslated corpus to work with OpusTrainer Tags
#

set -x
set -euo pipefail

echo "###### Generating alignments"
test -v BIN
test -v SRC
test -v TRG

original_prefix=$1
backtranslated_prefix=$2
output_original_prefix=$3
output_backtranslated_prefix=$4

COMPRESSION_CMD="${COMPRESSION_CMD:-pigz}"
ARTIFACT_EXT="${ARTIFACT_EXT:-gz}"

cd "$(dirname "${0}")"

output_dir=$(dirname "${output_original_prefix}")
mkdir -p "${output_dir}"
dir="${output_dir}/tmp"
mkdir -p "${dir}"

# train alignments on a merged corpus because fast_align is a statistical tool that benefits from a bigger corpus
# and might not be accurate on a smaller one, for example when we have fewer back-translations

# this is quite heavy on disk

echo "### Decompressing original corpus to get its length"
${COMPRESSION_CMD} -d "${original_prefix}.${SRC}.${ARTIFACT_EXT}"
original_len=$(wc -l "${original_prefix}.${SRC}")

echo "### Creating merged corpus"
  cat <(paste <(cat "${original_prefix}.${SRC}") <(${COMPRESSION_CMD} -dc "${original_prefix}.${TRG}.${ARTIFACT_EXT}")) \
      <(paste <(${COMPRESSION_CMD} -dc "${backtranslated_prefix}.${SRC}.${ARTIFACT_EXT}") <(${COMPRESSION_CMD} -dc "${backtranslated_prefix}.${TRG}.${ARTIFACT_EXT}")) |
  sed 's/\t/ ||| /' >"${dir}/corpus"

echo "### Training alignments"
  # forward
  "${BIN}/fast_align" -vod -i "${dir}/corpus" >"${dir}/align.s2t"
  # reversed
  "${BIN}/fast_align" -vodr -i "${dir}/corpus" >"${dir}/align.t2s"

echo "### Symmetrizing alignments"
  "${BIN}/atools" -i "${dir}/align.s2t" -j "${dir}/align.t2s" -c grow-diag-final-and >"${dir}/corpus.aln"

echo "### Splitting the aligned corpus back"
# take first N lines
head -n ${original_len} "${dir}/corpus.aln" |
  ${COMPRESSION_CMD} >"${output_original_prefix}.aln.${ARTIFACT_EXT}"
# take lines starting with N+1
tail -n +$((${original_len}+1)) "${dir}/corpus.aln" |
  ${COMPRESSION_CMD} >"${output_backtranslated_prefix}.aln.${ARTIFACT_EXT}"

echo "### Deleting tmp dir"
rm -rf "${dir}"

echo "###### Done: Generating alignments"

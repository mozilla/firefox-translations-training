#!/bin/bash
##
# Generates whitespace tokenized alignments jointly on original and back-translated corpus to work with OpusTrainer Tags
#
# It is used in the teacher model after back-translations
#
# OpusTrainer does not support SentencePiece tokenized alignments as input.
# It will remap the whitespace tokenized alignments to match SentencePiece tokenization before passing to Marian.
#

set -x
set -euo pipefail

echo "###### Generating alignments"
[[ -z "${BIN}" ]] && echo "BIN is empty"
[[ -z "${SRC}" ]] && echo "SRC is empty"
[[ -z "${TRG}" ]] && echo "TRG is empty"

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
original_len=$(wc -l <"${original_prefix}.${SRC}")

echo "### Creating merged corpus from the original and back-translated ones"
cat <(cat "${original_prefix}.${SRC}") <(${COMPRESSION_CMD} -dc "${backtranslated_prefix}.${SRC}.${ARTIFACT_EXT}")  \
  > "${dir}/corpus.${SRC}"
cat <(${COMPRESSION_CMD} -dc "${original_prefix}.${TRG}.${ARTIFACT_EXT}") <(${COMPRESSION_CMD} -dc "${backtranslated_prefix}.${TRG}.${ARTIFACT_EXT}") \
  > "${dir}/corpus.${TRG}"

echo "### Training alignments"
# eflomal is supposed to use less memory than fast_align with competitive quality
eflomal-align -s "${dir}/corpus.${SRC}" -t "${dir}/corpus.${TRG}" -f "${dir}/align.s2t" -r "${dir}/align.t2s"
rm "${dir}/corpus.${SRC}"
rm "${dir}/corpus.${TRG}"

echo "### Symmetrizing alignments"
"${BIN}/atools" -i "${dir}/align.s2t" -j "${dir}/align.t2s" -c grow-diag-final-and >"${dir}/corpus.aln"
rm "${dir}/align.s2t"
rm "${dir}/align.t2s"

echo "### Splitting the aligned corpus back"
# take first N lines
head -n ${original_len} "${dir}/corpus.aln" |
  ${COMPRESSION_CMD} >"${output_original_prefix}.aln.${ARTIFACT_EXT}"
# take lines starting with N+1
tail -n +$(($original_len+1)) "${dir}/corpus.aln" |
  ${COMPRESSION_CMD} >"${output_backtranslated_prefix}.aln.${ARTIFACT_EXT}"

echo "### Deleting tmp dir"
rm -rf "${dir}"

echo "###### Done: Generating alignments"

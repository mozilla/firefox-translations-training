#!/bin/bash
##
# Generates whitespace tokenized alignments to work with OpusTrainer Tags
#
# It is used in student training
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

corpus_prefix=$1
output_prefix=$2

COMPRESSION_CMD="${COMPRESSION_CMD:-pigz}"
ARTIFACT_EXT="${ARTIFACT_EXT:-gz}"

cd "$(dirname "${0}")"

output_dir=$(dirname "${output_prefix}")
mkdir -p "${output_dir}"
dir="${output_dir}/tmp"
mkdir -p "${dir}"

echo "### Decompressing corpus"
${COMPRESSION_CMD} -d --rm "${corpus_prefix}.${SRC}.${ARTIFACT_EXT}"
${COMPRESSION_CMD} -d --rm "${corpus_prefix}.${TRG}.${ARTIFACT_EXT}"

echo "### Training alignments"
# eflomal is supposed to use less memory than fast_align with competitive quality
eflomal-align -v -s "${corpus_prefix}.${SRC}" -t "${corpus_prefix}.${TRG}" -f "${dir}/align.s2t" -r "${dir}/align.t2s"

echo "### Symmetrizing alignments"
"${BIN}/atools" -i "${dir}/align.s2t" -j "${dir}/align.t2s" -c grow-diag-final-and |
  ${COMPRESSION_CMD} >"${output_prefix}.aln.${ARTIFACT_EXT}"


echo "### Deleting tmp dir"
rm -rf "${dir}"

echo "###### Done: Generating alignments"

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

echo "### Decompressing"
${COMPRESSION_CMD} -d --rm "${original_prefix}.${SRC}.${ARTIFACT_EXT}"
${COMPRESSION_CMD} -d --rm "${original_prefix}.${TRG}.${ARTIFACT_EXT}"
${COMPRESSION_CMD} -d --rm "${backtranslated_prefix}.${SRC}.${ARTIFACT_EXT}"
${COMPRESSION_CMD} -d --rm "${backtranslated_prefix}.${TRG}.${ARTIFACT_EXT}"

echo "### Training alignments for corpus"
# eflomal is supposed to use less memory than fast_align with competitive quality
eflomal-align -v \
  -s "${original_prefix}.${SRC}" -t "${original_prefix}.${TRG}" \
  -f "${dir}/corpus.s2t" -r "${dir}/corpus.t2s"

echo "### Calculating priors (alignments model)"
eflomal-makepriors -v \
  -s "${original_prefix}.${SRC}" -t "${original_prefix}.${TRG}" \
  -f "${dir}/corpus.s2t" -r "${dir}/corpus.t2s" \
  -p "${output_original_prefix}.priors"

echo "### Using the priors to align back-translations"
eflomal-align -v \
  -s "${backtranslated_prefix}.${SRC}" -t "${backtranslated_prefix}.${TRG}" \
  -f "${dir}/mono.s2t" -r "${dir}/mono.t2s" \
  -p "${output_original_prefix}.priors"

echo "### Symmetrizing alignments"
"${BIN}/atools" -i "${dir}/corpus.s2t" -j "${dir}/corpus.t2s" -c grow-diag-final-and |
  ${COMPRESSION_CMD} >"${output_original_prefix}.aln.${ARTIFACT_EXT}"
"${BIN}/atools" -i "${dir}/mono.s2t" -j "${dir}/mono.t2s" -c grow-diag-final-and |
  ${COMPRESSION_CMD} >"${output_backtranslated_prefix}.aln.${ARTIFACT_EXT}"


echo "### Deleting tmp dir"
rm -rf "${dir}"

echo "###### Done: Generating alignments"

#!/bin/bash
##
# Generates Moses tokenized alignment to work with OpusTrainer Tags
#

set -x
set -euo pipefail

echo "###### Generating alignments"
test -v BIN
test -v SRC
test -v TRG

corpus_prefix=$1
output_prefix=$2
threads=$3

COMPRESSION_CMD="${COMPRESSION_CMD:-pigz}"
ARTIFACT_EXT="${ARTIFACT_EXT:-gz}"

if [ "$threads" = "auto" ]; then
  threads=$(nproc)
fi

cd "$(dirname "${0}")"

output_dir=$(dirname "${output_prefix}")
mkdir -p "${output_dir}"
dir="${output_dir}/tmp"
mkdir -p "${dir}"

echo "### Tokenization"
# Example of moses tokenized text:
# The little girl , seeing she had lost one of her pretty shoes , grew angry , and said to the Witch , “ Give me back my shoe ! ”
${COMPRESSION_CMD} -dc "${corpus_prefix}.${SRC}.${ARTIFACT_EXT}" |
  sacremoses -l ${SRC} -j ${threads} tokenize |
  ${COMPRESSION_CMD} >"${dir}/corpus.moses.${SRC}.${ARTIFACT_EXT}"
${COMPRESSION_CMD} -dc "${corpus_prefix}.${TRG}.${ARTIFACT_EXT}" |
  sacremoses -l ${TRG} -j ${threads} tokenize |
  ${COMPRESSION_CMD} >"${dir}/corpus.moses.${TRG}.${ARTIFACT_EXT}"

echo "### Creating merged corpus"
test -s "${output_prefix}.aln.${ARTIFACT_EXT}" || test -s "${dir}/corpus" ||
  paste <(${COMPRESSION_CMD} -dc "${dir}/corpus.moses.${SRC}.${ARTIFACT_EXT}") <(${COMPRESSION_CMD} -dc "${dir}/corpus.moses.${TRG}.${ARTIFACT_EXT}") |
  sed 's/\t/ ||| /' >"${dir}/corpus"

echo "### Training alignments"
test -s "${output_prefix}.aln.${ARTIFACT_EXT}" || test -s "${dir}/align.s2t.${ARTIFACT_EXT}" ||
  "${BIN}/fast_align" -vod -i "${dir}/corpus" |
  ${COMPRESSION_CMD} >"${dir}/align.s2t.${ARTIFACT_EXT}"
test -s "${output_prefix}.aln.${ARTIFACT_EXT}" || test -s "${dir}/align.t2s.${ARTIFACT_EXT}" ||
  "${BIN}/fast_align" -vodr -i "${dir}/corpus" |
  ${COMPRESSION_CMD} >"${dir}/align.t2s.${ARTIFACT_EXT}"

echo "### Symmetrizing alignments"
test -s "${output_prefix}.aln.${ARTIFACT_EXT}" || test -s "${dir}/align.t2s" ||
  ${COMPRESSION_CMD} -d "${dir}/align.s2t.${ARTIFACT_EXT}" "${dir}/align.t2s.${ARTIFACT_EXT}"
test -s "${output_prefix}.aln.${ARTIFACT_EXT}" ||
  "${BIN}/atools" -i "${dir}/align.s2t" -j "${dir}/align.t2s" -c grow-diag-final-and |
  ${COMPRESSION_CMD} >"${output_prefix}.aln.${ARTIFACT_EXT}"


echo "### Deleting tmp dir"
rm -rf "${dir}"

echo "###### Done: Generating alignments"

#!/bin/bash
##
# Generates whitespace tokenized alignments to work with OpusTrainer Tags
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

echo "### Creating merged corpus"
paste <(${COMPRESSION_CMD} -dc "${corpus_prefix}.${SRC}.${ARTIFACT_EXT}") <(${COMPRESSION_CMD} -dc "${corpus_prefix}.${TRG}.${ARTIFACT_EXT}") |
  sed 's/\t/ ||| /' >"${dir}/corpus"

echo "### Training alignments"
# forward
"${BIN}/fast_align" -vod -i "${dir}/corpus" >"${dir}/align.s2t"
# reversed
"${BIN}/fast_align" -vodr -i "${dir}/corpus" >"${dir}/align.t2s"

echo "### Symmetrizing alignments"
"${BIN}/atools" -i "${dir}/align.s2t" -j "${dir}/align.t2s" -c grow-diag-final-and |
  ${COMPRESSION_CMD} >"${output_prefix}.aln.${ARTIFACT_EXT}"


echo "### Deleting tmp dir"
rm -rf "${dir}"

echo "###### Done: Generating alignments"

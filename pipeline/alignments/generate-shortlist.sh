#!/bin/bash
##
# Generates a lexical shortlist for a corpus.
#
#
# It also generate SentencePiece tokenized alignments that are required for extract_lex
#

set -x
set -euo pipefail

echo "###### Generating alignments and shortlist"
[[ -z "${MARIAN}" ]] && echo "MARIAN is empty"
[[ -z "${BIN}" ]] && echo "BIN is empty"
[[ -z "${SRC}" ]] && echo "SRC is empty"
[[ -z "${TRG}" ]] && echo "TRG is empty"

corpus_prefix=$1
vocab_path=$2
output_dir=$3
threads=$4

COMPRESSION_CMD="${COMPRESSION_CMD:-pigz}"
ARTIFACT_EXT="${ARTIFACT_EXT:-gz}"

if [ "$threads" = "auto" ]; then
  threads=$(nproc)
fi

cd "$(dirname "${0}")"

mkdir -p "${output_dir}"
dir="${output_dir}/tmp"
mkdir -p "${dir}"

corpus_src="${corpus_prefix}.${SRC}.${ARTIFACT_EXT}"
corpus_trg="${corpus_prefix}.${TRG}.${ARTIFACT_EXT}"


echo "### Subword segmentation with SentencePiece"
${COMPRESSION_CMD} -dc "${corpus_src}" |
  parallel --no-notice --pipe -k -j "${threads}" --block 50M "${MARIAN}/spm_encode" --model "${vocab_path}" \
   >"${dir}/corpus.spm.${SRC}"

${COMPRESSION_CMD} -dc "${corpus_trg}" |
  parallel --no-notice --pipe -k -j "${threads}" --block 50M "${MARIAN}/spm_encode" --model "${vocab_path}" \
   >"${dir}/corpus.spm.${TRG}"

echo "### Training alignments"
# eflomal is supposed to use less memory than fast_align with competitive quality
eflomal-align -v -s "${dir}/corpus.spm.${SRC}" -t "${dir}/corpus.spm.${TRG}" -f "${dir}/align.s2t" -r "${dir}/align.t2s"

echo "### Symmetrizing alignments"
"${BIN}/atools" -i "${dir}/align.s2t" -j "${dir}/align.t2s" -c grow-diag-final-and \
  >"${output_dir}/corpus.aln"

rm "${dir}/align.s2t"
rm "${dir}/align.t2s"

echo "### Creating shortlist"
"${BIN}/extract_lex" \
  "${dir}/corpus.spm.${TRG}" \
  "${dir}/corpus.spm.${SRC}" \
  "${output_dir}/corpus.aln" \
  "${dir}/lex.s2t" \
  "${dir}/lex.t2s"

if [ -f "${dir}/lex.s2t" ]; then
  ${COMPRESSION_CMD} "${dir}/lex.s2t"
fi

rm "${dir}/corpus.spm.${TRG}"
rm "${dir}/corpus.spm.${SRC}"
rm "${output_dir}/corpus.aln"

echo "### Shortlist pruning"
"${MARIAN}/spm_export_vocab" --model="${vocab_path}" --output="${dir}/vocab.txt"
${COMPRESSION_CMD} -dc "${dir}/lex.s2t.${ARTIFACT_EXT}" |
  grep -v NULL |
  python3 "prune_shortlist.py" 100 "${dir}/vocab.txt" |
  ${COMPRESSION_CMD} >"${output_dir}/lex.s2t.pruned.${ARTIFACT_EXT}"

echo "### Deleting tmp dir"
rm -rf "${dir}"

echo "###### Done: Generating alignments and shortlist"

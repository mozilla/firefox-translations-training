#!/bin/bash
##
# Generates alignment and lexical shortlist for a corpus.
#

set -x
set -euo pipefail

echo "###### Generating alignments and shortlist"
test -v MARIAN
test -v BIN
test -v SRC
test -v TRG

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
test -s "${dir}/corpus.spm.${SRC}.${ARTIFACT_EXT}" ||
  ${COMPRESSION_CMD} -dc "${corpus_src}" |
  parallel --no-notice --pipe -k -j "${threads}" --block 50M "${MARIAN}/spm_encode" --model "${vocab_path}" |
  ${COMPRESSION_CMD} >"${dir}/corpus.spm.${SRC}.${ARTIFACT_EXT}"
test -s "${dir}/corpus.spm.${TRG}.${ARTIFACT_EXT}" ||
  ${COMPRESSION_CMD} -dc "${corpus_trg}" |
  parallel --no-notice --pipe -k -j "${threads}" --block 50M "${MARIAN}/spm_encode" --model "${vocab_path}" |
  ${COMPRESSION_CMD} >"${dir}/corpus.spm.${TRG}.${ARTIFACT_EXT}"

echo "### Creating merged corpus"
test -s "${output_dir}/corpus.aln.${ARTIFACT_EXT}" || test -s "${dir}/corpus" ||
  paste <(${COMPRESSION_CMD} -dc "${dir}/corpus.spm.${SRC}.${ARTIFACT_EXT}") <(${COMPRESSION_CMD} -dc "${dir}/corpus.spm.${TRG}.${ARTIFACT_EXT}") |
  sed 's/\t/ ||| /' >"${dir}/corpus"

echo "### Training alignments"
test -s "${output_dir}/corpus.aln.${ARTIFACT_EXT}" || test -s "${dir}/align.s2t.${ARTIFACT_EXT}" ||
  "${BIN}/fast_align" -vod -i "${dir}/corpus" |
  ${COMPRESSION_CMD} >"${dir}/align.s2t.${ARTIFACT_EXT}"
test -s "${output_dir}/corpus.aln.${ARTIFACT_EXT}" || test -s "${dir}/align.t2s.${ARTIFACT_EXT}" ||
  "${BIN}/fast_align" -vodr -i "${dir}/corpus" |
  ${COMPRESSION_CMD} >"${dir}/align.t2s.${ARTIFACT_EXT}"

echo "### Symmetrizing alignments"
test -s "${output_dir}/corpus.aln.${ARTIFACT_EXT}" || test -s "${dir}/align.t2s" ||
  ${COMPRESSION_CMD} -d "${dir}/align.s2t.${ARTIFACT_EXT}" "${dir}/align.t2s.${ARTIFACT_EXT}"
test -s "${output_dir}/corpus.aln.${ARTIFACT_EXT}" ||
  "${BIN}/atools" -i "${dir}/align.s2t" -j "${dir}/align.t2s" -c grow-diag-final-and |
  ${COMPRESSION_CMD} >"${output_dir}/corpus.aln.${ARTIFACT_EXT}"

echo "### Creating shortlist"
test -s "${dir}/lex.s2t.${ARTIFACT_EXT}" ||
  # extract_lex doesn't support zstd natively; we need to
  # decrypt first
  if [ "${ARTIFACT_EXT}" = "zst" ]; then
    zstdmt -d "${dir}/corpus.spm.${TRG}.${ARTIFACT_EXT}"
    zstdmt -d "${dir}/corpus.spm.${SRC}.${ARTIFACT_EXT}"
    zstdmt -d "${output_dir}/corpus.aln.${ARTIFACT_EXT}"
    "${BIN}/extract_lex" \
      "${dir}/corpus.spm.${TRG}" \
      "${dir}/corpus.spm.${SRC}" \
      "${output_dir}/corpus.aln" \
      "${dir}/lex.s2t" \
      "${dir}/lex.t2s"
    rm "${dir}/corpus.spm.${TRG}"
    rm "${dir}/corpus.spm.${SRC}"
    rm "${output_dir}/corpus.aln"
  else
    "${BIN}/extract_lex" \
      "${dir}/corpus.spm.${TRG}.${ARTIFACT_EXT}" \
      "${dir}/corpus.spm.${SRC}.${ARTIFACT_EXT}" \
      "${output_dir}/corpus.aln.${ARTIFACT_EXT}" \
      "${dir}/lex.s2t" \
      "${dir}/lex.t2s"
  fi

test -s "${dir}/lex.s2t" && ${COMPRESSION_CMD} "${dir}/lex.s2t"

echo "### Shortlist pruning"
test -s "${dir}/vocab.txt" ||
  "${MARIAN}/spm_export_vocab" --model="${vocab_path}" --output="${dir}/vocab.txt"
test -s "${output_dir}/lex.s2t.pruned.${ARTIFACT_EXT}" ||
  ${COMPRESSION_CMD} -dc "${dir}/lex.s2t.${ARTIFACT_EXT}" |
  grep -v NULL |
  python3 "prune_shortlist.py" 100 "${dir}/vocab.txt" |
  ${COMPRESSION_CMD} >"${output_dir}/lex.s2t.pruned.${ARTIFACT_EXT}"

echo "### Deleting tmp dir"
rm -rf "${dir}"

echo "###### Done: Generating alignments and shortlist"

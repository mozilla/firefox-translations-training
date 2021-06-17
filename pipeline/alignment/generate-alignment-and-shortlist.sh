#!/bin/bash
##
# Generates alignment and lexical shortlist for a corpus.
#
# Usage:
#   bash generate-alignment-and-shortlist.sh corpus_prefix vocab_path output_dir
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

test -e "${BIN}/atools" || exit 1
test -e "${BIN}/extract_lex" || exit 1
test -e "${BIN}/fast_align" || exit 1

mkdir -p "${output_dir}"
dir="${TMP}/alignment"
mkdir -p "${dir}"

corpus_src="${corpus_prefix}.${SRC}.gz"
corpus_trg="${corpus_prefix}.${TRG}.gz"

echo "### Subword segmentation with SentencePiece"
test -s "${dir}/corpus.spm.${SRC}.gz" ||
  pigz -dc "${corpus_src}" |
  parallel --no-notice --pipe -k -j "$(nproc)" --block 50M "${MARIAN}/spm_encode" --model "${vocab_path}" |
  pigz >"${dir}/corpus.spm.${SRC}.gz"
test -s "${dir}/corpus.spm.${TRG}.gz" ||
  pigz -dc "${corpus_trg}" |
  parallel --no-notice --pipe -k -j "$(nproc)" --block 50M "${MARIAN}/spm_encode" --model "${vocab_path}" |
  pigz >"${dir}/corpus.spm.${TRG}.gz"

echo "### Creating merged corpus"
test -s "${dir}/corpus.aln.gz" || test -s "${dir}/corpus" ||
  paste <(pigz -dc "${dir}/corpus.spm.${SRC}.gz") <(pigz -dc "${dir}/corpus.spm.${TRG}.gz") |
  sed 's/\t/ ||| /' >"${dir}/corpus"

echo "### Training alignments"
test -s "${dir}/corpus.aln.gz" ||
  test -s "${dir}/align.s2t.gz" ||
  "${BIN}/fast_align" -vod -i "${dir}/corpus" |
  pigz >"${dir}/align.s2t.gz"
test -s "${dir}/corpus.aln.gz" ||
  test -s "${dir}/align.t2s.gz" ||
  "${BIN}/fast_align" -vodr -i "${dir}/corpus" |
  pigz >"${dir}/align.t2s.gz"
test -s "${dir}/corpus" && rm "${dir}/corpus"

echo "### Symmetrizing alignments"
test -s "${dir}/corpus.aln.gz" || pigz -d "${dir}/align.s2t.gz" "${dir}/align.t2s.gz"
test -s "${dir}/corpus.aln.gz" ||
  "${BIN}/atools" -i "${dir}/align.s2t" -j "${dir}/align.t2s" -c grow-diag-final-and |
  pigz >"${dir}/corpus.aln.gz"
test -s "${dir}/align.s2t" && rm "${dir}"/align.???

echo "### Creating shortlist"
test -s "${dir}/lex.s2t.gz" ||
  "${BIN}/extract_lex" \
    "${dir}/corpus.spm.${TRG}.gz" \
    "${dir}/corpus.spm.${SRC}.gz" \
    "${dir}/corpus.aln.gz" \
    "${dir}/lex.s2t" \
    "${dir}/lex.t2s"
test -s "${dir}/lex.s2t" && pigz "${dir}/lex.s2t"

echo "### Cleaning"
test -s "${output_dir}/corpus.aln.gz" || rsync "${dir}/corpus.aln.gz" "${output_dir}/corpus.aln.gz"
test -e "${dir}/lex.t2s" && rm "${dir}/lex.t2s"

echo "### Shortlist pruning"
test -s "${dir}/vocab.txt" ||
  "${MARIAN}/spm_export_vocab" --model="${vocab_path}" --output="${dir}/vocab.txt"
test -s "${output_dir}/lex.s2t.pruned.gz" ||
  pigz -dc "${dir}/lex.s2t.gz" |
  grep -v NULL |
  python3 "${WORKDIR}/pipeline/alignment/prune_shortlist.py" 100 "${dir}/vocab.txt" |
  pigz >"${output_dir}/lex.s2t.pruned.gz"

echo "### Deleting tmp dir"
rm -rf "${dir}"

echo "###### Done: Generating alignments and shortlist"

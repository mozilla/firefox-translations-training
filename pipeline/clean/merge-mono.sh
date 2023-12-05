#!/bin/bash
##
# Merges monolingual datasets. The datasets are input as a glob-style string.
# Each file in that directory will be used as input. The files will be deduplicated,
# shuffled, and written out to a single archive.
#
# Kinds:
#   taskcluster/ci/merge-mono/kind.yml
#
# Example usage:
#
#   pipeline/clean/merge-mono.sh             \
#      /builds/worker/artifacts/mono.en.zst  \
#      100000000                             \
#      $MOZ_FETCHES_DIR/*.zst
#

set -x
set -euo pipefail
test -v BIN

echo "###### Merging monolingual datasets"

#                      Example inputs:
# The path to the output compressed file, e.g. "/builds/worker/artifacts/mono.en.zst"
output=$1
# The maximum number of sentences that will be merged. e.g. 100000000
# These sentences are randomly sampled from the datasets.
max_sentences=$2
# A glob-style path to the mono datasets, e.g. /path/to/*.zst
datasets=( "${@:3}" )

COMPRESSION_CMD="${COMPRESSION_CMD:-pigz}"

echo "### Merging the following datasets:"
ls $datasets

dir=$(dirname "${output}")
mkdir -p "${dir}"

${COMPRESSION_CMD} -dc "${datasets[@]}" |
  ${BIN}/dedupe |
  shuf -n "${max_sentences}" |
  ${COMPRESSION_CMD} >"${output}"


echo "###### Done: Merging monolingual datasets"

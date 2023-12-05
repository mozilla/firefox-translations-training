#!/bin/bash
##
# Merges monolingual datasets. The datasets are input as a glob-style string.
# Each file in that directory will be used as input. The files will be deduplicated,
# shuffled, and written out to a single archive.
#
# See: taskcluster/ci/merge-mono/kind.yml
#

set -x
set -euo pipefail
test -v BIN

echo "###### Merging monolingual datasets"

#                      Example inputs:
output=$1              # /builds/worker/artifacts/mono.en.zst
max_sentences=$2       # 100000000
datasets=( "${@:3}" )  # $MOZ_FETCHES_DIR/*.zst'

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

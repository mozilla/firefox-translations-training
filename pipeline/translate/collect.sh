#!/bin/bash
#
# Collects chunked translation data of the form "out-file.N.out" where N is a number.
# The datasets are initially chunked so that tasks can work on smaller sets of data
# to better parallelize the work. After processing, any chunked data is reassembled
# with this script.
#
# Example tasks running on chunked data (before this script):
#   extract-best-en-ca-1/10
#   translate-corpus-en-ca-1/10
#   translate-mono-src-en-ca-1/10
#   translate-mono-trg-en-ca-1/10
#
# Kinds:
#   taskcluster/ci/collect-mono-trg/kind.yml
#   taskcluster/ci/collect-mono-src/kind.yml
#   taskcluster/ci/collect-corpus/kind.yml
#
# Example usage:
#
#   pipeline/translate/collect.sh    \
#      fetches                       \
#      artifacts/mono.en.zst         \
#      $MOZ_FETCHES_DIR/mono.ca.zst

set -x
set -euo pipefail

# The directory with chunks of the form "fetches/out-file.N.out", where N is a number.
chunks_dir=$1
# The full file name path to the output compressed file, e.g. "artifacts/mono.en.zst"
output_path=$2
# The path to the monolingual data to compare against, e.g. "$MOZ_FETCHES_DIR/mono.hu.zst"
mono_path=$3


COMPRESSION_CMD="${COMPRESSION_CMD:-pigz}"

echo "### Collecting translations"

find "${chunks_dir}" -name '*.out' |  # For example, finds "fetches/out-file.1.out", "fetches/out-file.2.out", etc.
  sort -t '.' -k2,2n |                      # Sort by the number in "out-file.1.out", e.g. 1 here.
  xargs cat |                               # Combine all of these files together.
  ${COMPRESSION_CMD} >"${output_path}"

echo "### Comparing number of sentences in source and artificial target files"

src_len=$(${COMPRESSION_CMD} -dc "${mono_path}" | wc -l)
trg_len=$(${COMPRESSION_CMD} -dc "${output_path}" | wc -l)

if [ "${src_len}" != "${trg_len}" ]; then
  echo "### Error: length of ${mono_path} ${src_len} is different from ${output_path} ${trg_len}"
  exit 1
fi

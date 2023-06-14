#!/bin/bash

set -x
set -euo pipefail

type=$1
chunks=$2
output_dir=$3
length=$4
lang_args=( "${@:5}" )

pushd `dirname $0`/../../.. &>/dev/null
VCS_ROOT=$(pwd)
popd &>/dev/null

if [ "${type}" = "mono" ]; then
  ${VCS_ROOT}/pipeline/translate/split-mono.sh "${lang_args[@]}" "${output_dir}" "${length}"
elif [ "${type}" = "corpus" ]; then
  ${VCS_ROOT}/pipeline/translate/split-corpus.sh "${lang_args[@]}" "${output_dir}" "${length}"
else
  echo "Unknown split type: ${type}"
  exit 1
fi

# Taskcluster requires a consistent number of chunks; split the resulting files
# evenly into the requested number of chunks, creating empty archives if there's
# not enough files to go around.
cd "${output_dir}"
ls file* | sort > all-files.txt
for i in $(seq 1 ${chunks} | tr '\n' ' '); do
  files=$(split -n l/${i}/${chunks} all-files.txt | tr '\n' ' ')
  if [ "${files}" = "" ]; then
    touch "split-file.${i}"
  else
    cat ${files} > "split-file.${i}"
  fi
  zstd --rm "split-file.${i}"
done

rm file* all-files.txt

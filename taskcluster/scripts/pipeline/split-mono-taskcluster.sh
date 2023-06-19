#!/bin/bash

set -x
set -euo pipefail

chunks=$1
output_dir=$2
length=$3
lang_args=( "${@:4}" )

pushd `dirname $0`/../../.. &>/dev/null
VCS_ROOT=$(pwd)
popd &>/dev/null

${VCS_ROOT}/pipeline/translate/split-mono.sh "${lang_args[@]}" "${output_dir}" "${length}"

# Taskcluster requires a consistent number of chunks; split the resulting files
# evenly into the requested number of chunks, creating empty archives if there's
# not enough files to go around.
cd "${output_dir}"
ls file* | sort > src-files.txt
for i in $(seq 1 ${chunks} | tr '\n' ' '); do
  src_files=$(split -n l/${i}/${chunks} src-files.txt | tr '\n' ' ')
  if [ "${src_files}" = "" ]; then
    touch "src-file.${i}"
  else
    cat ${src_files} > "src-file.${i}"
  fi
  zstd --rm "src-file.${i}"
done

rm file* src-files.txt

#!/bin/bash

set -x
set -euo pipefail

input=$1
output_dir=$2
other_args=( "${@:3}" )

pushd `dirname $0`/../../.. &>/dev/null
VCS_ROOT=$(pwd)
popd &>/dev/null

mkdir -p "${output_dir}"

zstd -d --rm "${input}"
input="${input%.zst}"
# In Taskcluster, we always parallelize this step N ways. In rare cases, there
# may not be enough input files to feed all of these jobs. If we received an
# empty input file we have nothing to do other than copying the empty file
# to the output file, simulating successfully completion.
if [ -s "${input}" ]; then
  ${VCS_ROOT}/pipeline/translate/translate.sh "${input}" "${other_args[@]}"
else
  cp "${input}" "${input}".out
fi

zstd --rm "${input}.out"
cp "${input}.out.zst" "${output_dir}"

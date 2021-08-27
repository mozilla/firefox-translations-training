#!/bin/bash
##
# Splits a monolingual dataset
#


set -x
set -euo pipefail

mono_path=$1
output_dir=$3
chunks=$3

mkdir -p "${output_dir}"
pigz -dc "${mono_path}" | split -d -n ${chunks} - "${output_dir}/file."
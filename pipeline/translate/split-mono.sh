#!/bin/bash
##
# Splits a monolingual dataset
#


set -x
set -euo pipefail

mono_path=$1
output_dir=$2
chunks=$3

mkdir -p "${output_dir}"
part_len=$(($(pigz -dc "${mono_path}" | wc -l) / ${chunks} + 1))
pigz -dc "${mono_path}" | split -d -l ${part_len} - "${output_dir}/file."
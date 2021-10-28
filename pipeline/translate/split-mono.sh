#!/bin/bash
##
# Splits a monolingual dataset
#


set -x
set -euo pipefail

mono_path=$1
output_dir=$2
length=$3

mkdir -p "${output_dir}"
pigz -dc "${mono_path}" | split -d -l ${length} - "${output_dir}/file."
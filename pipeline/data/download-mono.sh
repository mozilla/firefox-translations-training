#!/bin/bash
##
# Downloads monolingual datasets
#

set -x
set -euo pipefail

dataset=$1
lang=$2
max_sent=$3
output_prefix=$4
coef=0.1

echo "###### Downloading monolingual data for language ${lang} dataset ${dataset}"

tmp=$(dirname "${output_prefix}")/mono
mkdir -p "${tmp}"

echo "### Downloading dataset"
original_prefix="${tmp}/${dataset}.original.${lang}"
output_file_name="${output_prefix}.${lang}.gz"
name=${dataset#*_}
type=${dataset%%_*}

test -s "${original_prefix}.gz" ||
  bash "pipeline/data/importers/mono/${type}.sh" "${lang}" "${original_prefix}" "${name}"

echo "### Sampling dataset"
# temporary disable pipefail because perl operation causes SIGPIPE (141)
set +o pipefail
test -s "${output_file_name}" ||
  pigz -dc "${original_prefix}.gz" |
  shuf -n "$(bc -l <<<"${max_sent}+${max_sent}*${coef}")" |
  perl -ne 'print if(split(/\s/, $_) < 100)' |
  head -n "${max_sent}" |
  pigz >"${output_file_name}"
set -o pipefail

rm -rf "${original_prefix}.gz"

echo "###### Done: Downloading monolingual data"

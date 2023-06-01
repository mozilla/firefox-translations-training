#!/bin/bash
##
# Downloads monolingual datasets
#

set -x
set -euo pipefail

dataset=$1
lang=$2
max_sent=$3
output_path=$4
coef=0.1

echo "###### Downloading monolingual data for language ${lang} dataset ${dataset}"

cd "$(dirname "${0}")"

tmp=$(dirname "${output_path}")/original
mkdir -p "${tmp}"

echo "### Downloading dataset"
original_prefix="${tmp}/${dataset}.original.${lang}"
name=${dataset#*_}
type=${dataset%%_*}

test -s "${original_prefix}.gz" ||
  bash "importers/mono/${type}.sh" "${lang}" "${original_prefix}" "${name}"

echo "### Sampling dataset"
# temporary disable pipefail because perl operation causes SIGPIPE (141)
set +o pipefail
pigz -dc "${original_prefix}.gz" |
shuf -n "$(bc -l <<<"${max_sent}+${max_sent}*${coef}")" |
perl -ne 'print if(split(/\s/, $_) < 100)' |
head -n "${max_sent}" |
pigz >"${output_path}"
set -o pipefail

rm -rf "${original_prefix}.gz"

echo "###### Done: Downloading monolingual data"

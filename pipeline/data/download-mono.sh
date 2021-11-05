#!/bin/bash
##
# Downloads monolingual datasets
#

set -x
set -euo pipefail

echo "###### Downloading monolingual data"

dataset=$1
lang=$2
max_sent=$3
prefix=$4

#todo: fix downloading
file_name="${prefix}.${lang}.gz"
dir=$(dirname "${prefix}")/mono

if [ ! -e "${file_name}" ]; then
  echo "### Downloading monolingual corpus for ${lang}"
  mkdir -p "${dir}"
  coef=0.1

  echo "### Downloading dataset ${dataset}"
  source_prefix="${dir}/${dataset}.original.${lang}"
  gz_path="${dir}/${dataset}.${lang}.gz"
  name=${dataset#*_}
  type=${dataset%%_*}

  test -s "${source_prefix}.gz" ||
    bash "pipeline/data/importers/mono/${type}.sh" "${lang}" "${source_prefix}" "${name}"

  echo "### Sampling dataset ${dataset}"
  # temporary disable pipefail because perl operation causes SIGPIPE (141)
  set +o pipefail
  test -s "${gz_path}" ||
    pigz -dc "${source_prefix}.gz" |
    shuf -n "$(bc -l <<<"${max_sent}+${max_sent}*${coef}")" |
    perl -ne 'print if(split(/\s/, $_) < 100)' |
    head -n "${max_sent}" |
    pigz >"${gz_path}"
  set -o pipefail

  rm "${source_prefix}"*

fi

test -s "${file_name}"

echo "###### Done: Downloading monolingual data"

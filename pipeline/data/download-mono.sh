#!/bin/bash
##
# Downloads datasets
#
# Usage:
#   bash download-mono.sh lang max_sentences output_prefix dataset [dataset...]
#

set -x
set -euo pipefail

echo "###### Downloading monolingual data"

lang=$1
max_sent=$2
prefix=$3
cache=$4

file_name="${prefix}.${lang}.gz"
dir=$(dirname "${prefix}")/mono

if [ ! -e "${file_name}" ]; then
  echo "### Downloading monolingual corpus for ${lang}"
  mkdir -p "${dir}"
  coef=0.1

  for dataset in "${@:5}"; do
    echo "### Downloading dataset ${dataset}"
    source_prefix="${dir}/${dataset}.original.${lang}"
    gz_path="${dir}/${dataset}.${lang}.gz"
    name=${dataset#*_}
    type=${dataset%%_*}

    test -s "${source_prefix}.gz" ||
      bash "${WORKDIR}/pipeline/data/importers/mono/${type}.sh" "${lang}" "${source_prefix}" "${name}"

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
  done

  pigz -dc "${dir}"/*."${lang}".gz | shuf -n "${max_sent}" | pigz >"${file_name}"

fi

test -s "${file_name}"

lines=$(pigz -dc "${file_name}" | wc -l)
echo "### Number of sentences: ${lines}"

echo "###### Done: Downloading monolingual data"

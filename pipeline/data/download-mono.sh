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

COMPRESSION_CMD="${COMPRESSION_CMD:-pigz}"
ARTIFACT_EXT="${ARTIFACT_EXT:-gz}"

echo "###### Downloading monolingual data for language ${lang} dataset ${dataset}"

cd "$(dirname "${0}")"

tmp=$(dirname "${output_path}")/original
mkdir -p "${tmp}"

echo "### Downloading dataset"
original_prefix="${tmp}/${dataset}.original.${lang}"
name=${dataset#*_}
type=${dataset%%_*}

test -s "${original_prefix}.${ARTIFACT_EXT}" ||
  bash "importers/mono/${type}.sh" "${lang}" "${original_prefix}" "${name}"

echo "### Sampling dataset"
# temporary disable pipefail because perl operation causes SIGPIPE (141)
set +o pipefail
${COMPRESSION_CMD} -dc "${original_prefix}.${ARTIFACT_EXT}" |
shuf -n "$(bc -l <<<"scale=0; (${max_sent}+${max_sent}*${coef}) / 1")" |
perl -ne 'print if(split(/\s/, $_) < 100)' |
head -n "${max_sent}" |
${COMPRESSION_CMD} >"${output_path}"
set -o pipefail

rm -rf "${original_prefix}.${ARTIFACT_EXT}"

echo "###### Done: Downloading monolingual data"

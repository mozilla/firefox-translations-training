#!/bin/bash
##
# Cleans corpus using bicleaner-ai or bicleaner
#
# Usage:
#   bash bicleaner.sh corpus_prefix output_prefix
#

set -x
set -euo pipefail

echo "###### Bicleaner filtering"

test -v SRC
test -v TRG

corpus_prefix=$1
output_prefix=$2

output_dir=$(dirname "${output_prefix}")
mkdir -p "${output_dir}"
tmp_dir="${output_dir}/tmp"
mkdir -p "${tmp_dir}"

threshold=0.7
download_path=${TMP}/bicleaner.yml
bicleaner_url="https://github.com/bitextor/bicleaner-ai-data/releases/latest/download"
bicleaner_ai_url="https://github.com/bitextor/bicleaner-ai-data/releases/latest/download"

invalid_url() {
  wget -S --spider -o - $1 | grep -q '404 Not Found'
}

download_pack() {
  local url=$1
  local type="full"
  echo "### Downloading bicleaner language pack ${url}"

  if invalid_url "${url}/${type}-${SRC}-${TRG}.tgz"; then
    echo "### ${SRC}-${TRG} language pack does not exist, trying ${TRG}-${SRC}..."
    if invalid_url "${url}/${type}-${TRG}-${SRC}.tgz"; then
      echo "### ${TRG}-${SRC} language pack does not exist"
      return 1
    else
      wget -P "${download_path}" "${url}/${type}-${TRG}-${SRC}.tgz"
      tar xvf "${download_path}/${type}-${TRG}-${SRC}.tgz" -C "${download_path}"
      rm "${download_path}/${type}-${TRG}-${SRC}.tgz"
    fi
  else
    wget -P "${download_path}" "${url}/${type}-${SRC}-${TRG}.tgz"
    tar xvf "${download_path}/${type}-${SRC}-${TRG}.tgz" -C "${download_path}"
    rm "${download_path}/${type}-${SRC}-${TRG}.tgz"
  fi

  echo "### Bicleaner language pack ${url} is downloaded"
  return 0
}

if [ ! -e "${output_prefix}.${SRC}.gz" ]; then
  if download_pack $bicleaner_ai_url; then
    echo "### Using bicleaner-ai"
    cmd=bicleaner-ai-classify
  elif download_pack $bicleaner_url; then
    echo "### Using bicleaner"
    cmd=bicleaner-classify
  else
    echo "### Bicleaner language pack is not supported, skipping"
    exit 0
  fi
fi

echo "### Classifying and filtering"
test -s "${output_prefix}.${SRC}.gz" || test -s "${tmp_dir}/best.gz" ||
  paste <(pigz -dc "${corpus_prefix}.${SRC}.gz") <(pigz -dc "${corpus_prefix}.${TRG}.gz") |
  ${cmd} --scol 1 --tcol 1 - - "${download_path}" |
  awk "{if ($3>${threshold}) {print $0}}" | pigz >"${tmp_dir}/best.gz"

echo "### Writing output corpus"
test -s "${output_prefix}.${SRC}.gz" || pigz -dc "${tmp_dir}/best.gz" | cut -f1 | pigz >"${output_prefix}.${SRC}.gz"
test -s "${output_prefix}.${TRG}.gz" || pigz -dc "${tmp_dir}/best.gz" | cut -f2 | pigz >"${output_prefix}.${TRG}.gz"

echo "### Cleaning files"
rm -rf "${tmp_dir}"

echo "###### Done: Bicleaner filtering"

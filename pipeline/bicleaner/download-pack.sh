#!/bin/bash
##
# Downloads bicleaner-ai or bicleaner language pack
#

set -x
# don't use pipefail here because of wget check
set -eu

test -v SRC
test -v TRG

download_path=$1
type=$2

mkdir -p download_path

invalid_url() {
  wget -S --spider -o - $1 | grep -q '404 Not Found'
}

if [ "${type}" == 'bicleaner-ai' ]; then
    url="https://github.com/bitextor/bicleaner-ai-data/releases/latest/download"
    prefix="full-"
    extension="tgz"
elif [ "${type}" == 'bicleaner' ]; then
    url="https://github.com/bitextor/bicleaner-data/releases/latest/download"
    prefix=""
    extension="tar.gz"
else
  echo "Unsupported type: ${type}"
  exit 1
fi

echo "### Downloading ${type} language pack ${url}"

if invalid_url "${url}/${prefix}${SRC}-${TRG}.${extension}"; then
  echo "### ${SRC}-${TRG} language pack does not exist, trying ${TRG}-${SRC}..."
  if invalid_url "${url}/${prefix}${TRG}-${SRC}.${extension}"; then
    echo "### ${TRG}-${SRC} language pack does not exist"
    exit 1
  else
    lang1=$TRG
    lang2=$SRC
  fi
else
  lang1=$SRC
  lang2=$TRG
fi


wget -P "${download_path}" "${url}/${prefix}${lang1}-${lang2}.${extension}"
tar xvf "${download_path}/${prefix}${lang1}-${lang2}.${extension}" -C "${download_path}" --no-same-owner
mv "${download_path}/${lang1}-${lang2}"/* "${download_path}/"
rm "${download_path}/${prefix}${lang1}-${lang2}.${extension}"


echo "### ${type} language pack ${url} is downloaded"

#!/bin/bash
##
# Download latest versions of binaries from the Taskcluster toolchain
#
# See https://firefox-ci-tc.services.mozilla.com/tasks/index/translations.cache.level-1.toolchains.v3.fast-align/latest
#

set -x
set -euo pipefail


[[ -z "${BIN}" ]] && echo "BIN is empty"

if [ ! -d "${BIN}" ]; then
  echo "Downloading to ${BIN}"

  wget -P "${BIN}" https://firefox-ci-tc.services.mozilla.com/api/index/v1/task/translations.cache.level-1.toolchains.v3.extract-lex.latest/artifacts/public%2Fbuild%2Fextract_lex.tar.zst
  wget -P "${BIN}" https://firefox-ci-tc.services.mozilla.com/api/index/v1/task/translations.cache.level-1.toolchains.v3.fast-align.latest/artifacts/public%2Fbuild%2Ffast-align.tar.zst

  zstd -d "${BIN}"/*.zst

  for file in "${BIN}"/*.tar; do
    tar -xf "$file" --directory="${BIN}"
  done

  rm "${BIN}"/*.zst
  rm "${BIN}"/*.tar
else
    echo "Directory already exists, skipping"
fi

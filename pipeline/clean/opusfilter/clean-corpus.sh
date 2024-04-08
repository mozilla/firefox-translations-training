#!/bin/bash
##
# Cleaning parallel corpora with OpusFilter
#

set -x
set -euo pipefail

echo "###### Cleaning corpus with OpusFilter"

test -v SRC
test -v TRG

input_prefix=$1
output_prefix=$2
threads=$3
dataset=$4

COMPRESSION_CMD="${COMPRESSION_CMD:-pigz}"
ARTIFACT_EXT="${ARTIFACT_EXT:-gz}"

if [ "$threads" = "auto" ]; then
  threads=$(nproc)
fi

cd "$(dirname "${0}")"
dir="$(dirname "${output_prefix}")"
temp=$(mktemp -d)
mkdir -p ${dir}

wget -O ${temp}/lid.176.ftz https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz

#pip install laserembeddings
#python3 -m laserembeddings download-models

${COMPRESSION_CMD} -d --rm "${input_prefix}.${SRC}.${ARTIFACT_EXT}"
${COMPRESSION_CMD} -d --rm "${input_prefix}.${TRG}.${ARTIFACT_EXT}"

echo "### Generating cleaning config"
config_path=${dir}/generated-config.yml

opusfilter-autogen \
  --files "${input_prefix}.${SRC}" "${input_prefix}.${TRG}" \
  --langs en ru \
  --inter-dir ${temp} \
  --overwrite \
  --work-dir ${dir} \
  --output ${config_path} \
  --add-filter LanguageIDFilter "{\"id_method\": \"fasttext\", \"fasttext_model_path\": \"${temp}/lid.176.ftz\"}" \
  --add-filter CharacterScoreFilter '{"scripts": ["Latin", "Cyrillic"]}'  \
  --add-filter LengthRatioFilter.word '{"unit": "word"}' \
#  --add-filter LongWordFilter '{}' \
#  --add-filter SentenceEmbeddingFilter '{"languages": ["en","ru"]}' \
#  --add-filter LengthFilter '{}' \

test -s "${config_path}" || exit 1
cat "${config_path}"

echo "### Cleaning ${input_prefix}"

opusfilter \
  --overwrite \
  --n-jobs ${threads} \
  ${config_path}

pigz -d ${dir}/filtered.*

mv ${dir}/filtered.${SRC} ${output_prefix}.${SRC}
mv ${dir}/filtered.${TRG} ${output_prefix}.${TRG}

echo "### Checking length of the files"
new_len_src="$(cat "${output_prefix}.${SRC}" | wc -l)"
new_len_trg="$(cat "${output_prefix}.${TRG}" | wc -l)"
orig_len_src="$(cat "${input_prefix}.${SRC}" | wc -l)"
[[ ${new_len_src} -ge 1 ]] || exit 1
[[ ${new_len_trg} -ge 1 ]] || exit 1
[[ "${new_len_src}" = "${new_len_trg}" ]] || exit 1
echo "### Filtered length: ${new_len_src} / ${orig_len_src}"

${COMPRESSION_CMD} ${output_prefix}.${SRC}
${COMPRESSION_CMD} ${output_prefix}.${TRG}

test -s "${output_prefix}.${SRC}.${ARTIFACT_EXT}" || exit 1
test -s "${output_prefix}.${TRG}.${ARTIFACT_EXT}" || exit 1

echo "### Clean ${input_prefix} is written to  ${output_prefix}"

echo "###### Done: Cleaning corpus with OpusCleaner"

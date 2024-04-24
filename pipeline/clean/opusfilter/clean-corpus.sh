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
laser_scores=$5
bicleaner_scores=$6

COMPRESSION_CMD="${COMPRESSION_CMD:-pigz}"
ARTIFACT_EXT="${ARTIFACT_EXT:-gz}"

if [ "$threads" = "auto" ]; then
  threads=$(nproc)
fi

cd "$(dirname "${0}")"
dir="$(dirname "${output_prefix}")"
temp=$(mktemp -d)
mkdir -p ${dir}

echo "Downloading fast text model"
fasttext_path=${temp}/lid.176.bin
wget --quiet -O ${fasttext_path} https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin

${COMPRESSION_CMD} -d --rm "${input_prefix}.${SRC}.${ARTIFACT_EXT}"
${COMPRESSION_CMD} -d --rm "${input_prefix}.${TRG}.${ARTIFACT_EXT}"

echo "### Generating cleaning config"
config_path=${dir}/generated-config.yml

# TODO: there should be more robust logic here to determine script
if [ "$SRC" == 'ru' ]; then
  script1="Cyrillic"
else
  script1="Latin"
fi

if [ "$TRG" == 'ru' ]; then
  script2="Cyrillic"
else
  script2="Latin"
fi

# to add customfilter module
export PYTHONPATH=$(pwd)
export TQDM_DISABLE=1

python3 cache.py --opus_scores "${laser_scores}" --opus_filter_name SentenceEmbeddingFilter "${input_prefix}.${SRC}" "${input_prefix}.${TRG}" laser_scores.pickle
python3 cache.py --opus_scores "${bicleaner_scores}" --opus_filter_name BicleanerAI "${input_prefix}.${SRC}" "${input_prefix}.${TRG}" bicleaner_scores.pickle
#python3 cache.py "${input_prefix}.${SRC}" "${input_prefix}.${TRG}" laser_scores.pickle --opus_scores "${laser_scores}"  --opus_filter_name Laser3Filter

orig_len_src="$(cat "${input_prefix}.${SRC}" | wc -l)"
# todo: change to 100000
if [[ ${orig_len_src} -le 4000 ]]; then
  config_path="default.yml"
  sed -i -e "s#<src>#${SRC}#g" "${config_path}"
  sed -i -e "s#<trg>#${TRG}#g" "${config_path}"
  sed -i -e "s#<src_script>#${script1}#g" "${config_path}"
  sed -i -e "s#<trg_script>#${script2}#g" "${config_path}"
  sed -i -e "s#<src_input>#${input_prefix}.${SRC}#g" "${config_path}"
  sed -i -e "s#<trg_input>#${input_prefix}.${TRG}#g" "${config_path}"
  sed -i -e "s#<fasttext_path>#${fasttext_path}#g" "${config_path}"
else
  python3 autogen.py \
      --files "${input_prefix}.${SRC}" "${input_prefix}.${TRG}" \
      --langs en ru \
      --sample-size 1000000 \
      --inter-dir ${temp} \
      --overwrite \
      --work-dir ${dir} \
      --output ${config_path} \
      --add-filter LanguageIDFilter "{\"id_method\": \"fasttext\", \"fasttext_model_path\": \"lid.176.bin\"}" \
      --add-filter CustomAlphaRatioFilter.word "{\"languages\": [\"${SRC}\", \"${TRG}\"], \"unit\": \"word\"}"  \
      --add-filter CustomAlphaRatioFilter.char "{\"languages\": [\"${SRC}\", \"${TRG}\"], \"unit\": \"char\"}"  \
      --add-filter LengthRatioFilter.word '{"unit": "word"}' \
      --add-filter CustomCachedLaserSimilarity '{"path": "laser_scores.pickle"}' \
      --add-filter CustomCachedBicleanerAi '{"path": "bicleaner_scores.pickle"}'
    #  --add-filter SentenceEmbeddingFilter "{\"languages\": [\"${SRC}\",\"${TRG}\"]}" \

  echo "### Analyzing"
  cp ${temp}/scores.jsonl.gz "${output_prefix}.scores.jsonl.gz"
  pigz -d ${temp}/scores.jsonl.gz
  python3 scores.py list  ${temp}/scores.jsonl
  python3 scores.py describe  ${temp}/scores.jsonl > "${output_prefix}.stats"
  python3 scores.py hist --save_path "${output_prefix}.hist.png" ${temp}/scores.jsonl
  python3 scores.py corr --save_path "${output_prefix}.corr.png" ${temp}/scores.jsonl
  python3 scores.py scatter-matrix --save_path "${output_prefix}.scatter.png" ${temp}/scores.jsonl

fi

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
[[ ${new_len_src} -ge 1 ]] || exit 1
[[ ${new_len_trg} -ge 1 ]] || exit 1
[[ "${new_len_src}" = "${new_len_trg}" ]] || exit 1
echo "### Filtered length: ${new_len_src} / ${orig_len_src}"

${COMPRESSION_CMD} ${output_prefix}.${SRC}
${COMPRESSION_CMD} ${output_prefix}.${TRG}

test -s "${output_prefix}.${SRC}.${ARTIFACT_EXT}" || exit 1
test -s "${output_prefix}.${TRG}.${ARTIFACT_EXT}" || exit 1

echo "### Clean ${input_prefix} is written to  ${output_prefix}"

rm "${input_prefix}.${SRC}" "${input_prefix}.${TRG}" "${output_prefix}.${SRC}" "${output_prefix}.${TRG}"

echo "###### Done: Cleaning corpus with OpusCleaner"

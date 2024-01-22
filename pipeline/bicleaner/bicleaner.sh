#!/bin/bash
##
# Cleans corpus using bicleaner-ai
#
# See:
#   docs/bicleaner.md

set -x
set -euo pipefail

echo "###### Bicleaner filtering"

test -v SRC
test -v TRG
test -v CUDA_DIR
test -v CUDNN_DIR

# cuda and cudnn libs
export LD_LIBRARY_PATH=${CUDA_DIR}/lib64:${CUDNN_DIR}:${LD_LIBRARY_PATH:+LD_LIBRARY_PATH:}

corpus_prefix=$1
output_prefix=$2
bicleaner_threshold=$3
threads=$4
pack_dir=$5

COMPRESSION_CMD="${COMPRESSION_CMD:-pigz}"
ARTIFACT_EXT="${ARTIFACT_EXT:-gz}"

if [ "$threads" = "auto" ]; then
  threads=$(nproc)
fi

output_dir=$(dirname "${output_prefix}")
mkdir -p "${output_dir}"

if [ "${bicleaner_threshold}" == "0" ] || [ "${bicleaner_threshold}" == "0.0" ]; then
  echo "Threshold is 0, skipping filtering"
  cp "${corpus_prefix}.${SRC}.${ARTIFACT_EXT}" "${output_prefix}.${SRC}.${ARTIFACT_EXT}"
  cp "${corpus_prefix}.${TRG}.${ARTIFACT_EXT}" "${output_prefix}.${TRG}.${ARTIFACT_EXT}"
else

  export scol=1
  export tcol=2
  # Get model src-trg from metadata.yaml
  model_source_lang=$(grep "source_lang" ${pack_dir}/*.yaml | awk '{print $2}')
  model_target_lang=$(grep "target_lang" ${pack_dir}/*.yaml | awk '{print $2}')
  # for example if SRC-TRG = en-ru
  # the model can be: en-ru, ru-en, en-xx
  if [ ${model_source_lang} == ${TRG} ] || [ ${model_target_lang} == ${SRC} ]; then
    # swap columns
    export scol=2
    export tcol=1
  fi
  # disable hard rules for multilingual model
  if [ ${model_source_lang} == "xx" ] || [ ${model_target_lang} == "xx" ]; then
    export hardrules="--disable_hardrules"
  else
    export hardrules=""
  fi

  #Export cuda visible devices if empty or not set
  if [ -z "${CUDA_VISIBLE_DEVICES:-}" ]; then
    export CUDA_VISIBLE_DEVICES=$(nvidia-smi --query-gpu=index --format=csv,noheader);
  fi

  echo "### Classifying"
  if [ ${#CUDA_VISIBLE_DEVICES} -gt 1 ]; then # Use gnu-parallel'd bicleaner-ai if we have more than 1 GPU
       #Convert CUDA_VISIBLE_DEVICES to an array
       export CUDA_VISIBLE_ARRAY=(${CUDA_VISIBLE_DEVICES//,/ })
       #Turn on tensorflow logging in bicleaner-ai
       export TF_CPP_MIN_LOG_LEVEL=0
       #This function expects a bicleaner yaml and a 1-based index into the CUDA_VISIBLE_ARRAY
       #Example: /mnt/nanna0/nbogoych/data/data/fr-en/fr-en-prod/biclean/pack/metadata.yaml index_in_CUDA_VISIBLE_ARRAY+1
       biclean() {
               export CUDA_VISIBLE_ARRAY=(${CUDA_VISIBLE_DEVICES//,/ })
               export CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_ARRAY[$(($2-1))]}
               bicleaner-ai-classify ${hardrules} --scol ${scol} --tcol ${tcol} - - $1
       }
       export -f biclean
       # {%} is a 1-indexed job slot number from GNU parallel.  We use that as the 1-indexed offset in CUDA_VISIBLE_ARRAY
       paste <(${COMPRESSION_CMD} -dc "${corpus_prefix}.${SRC}.${ARTIFACT_EXT}") <(${COMPRESSION_CMD} -dc "${corpus_prefix}.${TRG}.${ARTIFACT_EXT}") |
       parallel -j ${#CUDA_VISIBLE_ARRAY[@]} --pipe -k --block 10M biclean "${pack_dir}"/*.yaml {%} |
       ${COMPRESSION_CMD} >"${output_prefix}.scored.${ARTIFACT_EXT}"
  else
   paste <(${COMPRESSION_CMD} -dc "${corpus_prefix}.${SRC}.${ARTIFACT_EXT}") <(${COMPRESSION_CMD} -dc "${corpus_prefix}.${TRG}.${ARTIFACT_EXT}") |
     bicleaner-ai-classify ${hardrules} --scol ${scol} --tcol ${tcol} --processes "${threads}"  - - "${pack_dir}"/*.yaml |
     ${COMPRESSION_CMD} >"${output_prefix}.scored.${ARTIFACT_EXT}"
  fi

  echo "### Filtering"
  ${COMPRESSION_CMD} -dc "${output_prefix}.scored.${ARTIFACT_EXT}" |
    awk -v threshold=${bicleaner_threshold} -F"\t" '{if ($3>threshold) {print $0}}' |
    ${COMPRESSION_CMD} >"${output_prefix}.best.${ARTIFACT_EXT}"

  ${COMPRESSION_CMD} -dc "${output_prefix}.scored.${ARTIFACT_EXT}" |
    awk -v threshold=${bicleaner_threshold} -F"\t" '{if ($3<=threshold) {print $0}}' |
    ${COMPRESSION_CMD} >"${output_prefix}.filtered.${ARTIFACT_EXT}"

  echo "Lines before filtering: $(${COMPRESSION_CMD} -dc "${output_prefix}.scored.${ARTIFACT_EXT}" | wc -l)"
  echo "Lines after filtering: $(${COMPRESSION_CMD} -dc "${output_prefix}.best.${ARTIFACT_EXT}" | wc -l)"

  echo "### Writing output corpus"
  ${COMPRESSION_CMD} -dc "${output_prefix}.best.${ARTIFACT_EXT}" |
    tee >(cut -f1 | ${COMPRESSION_CMD} >"${output_prefix}.${SRC}.${ARTIFACT_EXT}") |
    cut -f2 | ${COMPRESSION_CMD} >"${output_prefix}.${TRG}.${ARTIFACT_EXT}"

  # do not delete intermediate files to inspect them and tune the threshold
fi

echo "###### Done: Bicleaner filtering"

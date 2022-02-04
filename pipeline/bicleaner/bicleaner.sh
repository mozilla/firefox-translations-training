#!/bin/bash
##
# Cleans corpus using bicleaner-ai or bicleaner
#

set -x
set -euo pipefail

echo "###### Bicleaner filtering"

test -v SRC
test -v TRG

corpus_prefix=$1
output_prefix=$2
bicleaner_threshold=$3
type=$4
threads=$5
pack_dir=$6

output_dir=$(dirname "${output_prefix}")
mkdir -p "${output_dir}"

if [ "${bicleaner_threshold}" == "0" ]; then
  echo "Threshold is 0, skipping filtering"
  cp "${corpus_prefix}.${SRC}.gz" "${output_prefix}.${SRC}.gz"
  cp "${corpus_prefix}.${TRG}.gz" "${output_prefix}.${TRG}.gz"
else
  if [ "${type}" == 'bicleaner-ai' ]; then
    echo "### Using bicleaner-ai"
    cmd=bicleaner-ai-classify
  elif [ "${type}" == 'bicleaner' ]; then
    echo "### Using bicleaner"
    cmd=bicleaner-classify
  else
    echo "### Unsupported type: ${type}"
    exit 1
  fi

  scol=1
  tcol=2
  if [ -d "${pack_dir}/${TRG}-${SRC}" ]; then
    scol=2
    tcol=1
  fi

  #Export cuda visible devices if not set
  if [ ${#CUDA_VISIBLE_DEVICES} == 0 ]; then   export CUDA_VISIBLE_DEVICES=$(nvidia-smi --query-gpu=index --format=csv,noheader); fi

  echo "### Classifying"
  if [ "${type}" == 'bicleaner-ai' && ${#CUDA_VISIBLE_DEVICES} > 1 ]; then # Use gnu-parallel'd bicleaner-ai if we have more than 1 GPU
       #Convert CUDA_VISIBLE_DEVICES to an array
       export CUDA_VISIBLE_ARRAY=($CUDA_VISIBLE_DEVICES)
       #Turn on tensorflow logging in bicleaner-ai
       export TF_CPP_MIN_LOG_LEVEL=0
       #This function expects a bicleaner yaml and a 1-based index into the CUDA_VISIBLE_ARRAY
       #Example: /mnt/nanna0/nbogoych/data/data/fr-en/fr-en-prod/biclean/pack/metadata.yaml index_in_CUDA_VISIBLE_ARRAY+1
       biclean() {
               export CUDA_VISIBLE_ARRAY=($CUDA_VISIBLE_DEVICES)
               export CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_ARRAY[$(($2-1))]}
               bicleaner-ai-classify --scol 2 --tcol 1 - - $1
       }
       export -f biclean
       # {%} is a 1-indexed job slot number from GNU parallel.  We use that as the 1-indexed offset in CUDA_VISIBLE_ARRAY
       paste <(pigz -dc "${corpus_prefix}.${SRC}.gz") <(pigz -dc "${corpus_prefix}.${TRG}.gz") |
       parallel -j ${#CUDA_VISIBLE_ARRAY[@]} --pipe -k --block 10M biclean "${pack_dir}"/*.yaml {#} |
       pigz >"${output_prefix}.scored.gz"
  else
   paste <(pigz -dc "${corpus_prefix}.${SRC}.gz") <(pigz -dc "${corpus_prefix}.${TRG}.gz") |
     ${cmd} --scol ${scol} --tcol ${tcol} --processes "${threads}"  - - "${pack_dir}"/*.yaml |
     pigz >"${output_prefix}.scored.gz"
  fi

  echo "### Filtering"
  pigz -dc "${output_prefix}.scored.gz" |
    awk -v threshold=${bicleaner_threshold} -F"\t" '{if ($3>threshold) {print $0}}' |
    pigz >"${output_prefix}.best.gz"

  echo "Lines before filtering: $(pigz -dc "${output_prefix}.scored.gz" | wc -l)"
  echo "Lines after filtering: $(pigz -dc "${output_prefix}.best.gz" | wc -l)"

  echo "### Writing output corpus"
  pigz -dc "${output_prefix}.best.gz" |
    tee >(cut -f1 | pigz >"${output_prefix}.${SRC}.gz") |
    cut -f2 | pigz >"${output_prefix}.${TRG}.gz"

  # do not delete intermediate files to inspect them and tune the threshold
fi

echo "###### Done: Bicleaner filtering"

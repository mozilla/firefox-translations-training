#!/bin/bash
##
# Cleans corpus using bicleaner-ai or bicleaner
#

set -x
set -euo pipefail

echo "###### Bicleaner filtering"

test -v SRC
test -v TRG
test -v CUDA_DIR

export LD_LIBRARY_PATH=${CUDA_DIR}/lib64:${CONDA_PREFIX}/lib:${LD_LIBRARY_PATH}

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

  echo "### Classifying"
  paste <(pigz -dc "${corpus_prefix}.${SRC}.gz") <(pigz -dc "${corpus_prefix}.${TRG}.gz") |
    ${cmd} --scol ${scol} --tcol ${tcol} --processes "${threads}"  - - "${pack_dir}"/*.yaml |
    pigz >"${output_prefix}.scored.gz"

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

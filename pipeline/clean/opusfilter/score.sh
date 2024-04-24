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
output_path=$2

COMPRESSION_CMD="${COMPRESSION_CMD:-pigz}"
ARTIFACT_EXT="${ARTIFACT_EXT:-gz}"

# for laser 1
# conflicts with opusfilter
pip install laserembeddings
python3 -m laserembeddings download-models

${COMPRESSION_CMD} -d --rm "${input_prefix}.${SRC}.${ARTIFACT_EXT}"
${COMPRESSION_CMD} -d --rm "${input_prefix}.${TRG}.${ARTIFACT_EXT}"

echo "###### Scoring"

opusfilter-cmd score \
  --inputs "${input_prefix}.${SRC}" "${input_prefix}.${TRG}" \
  --output "${output_path}" \
  --filters "[{\"SentenceEmbeddingFilter\": {\"languages\": [\"${SRC}\", \"${TRG}\"]}}]"

  #--filters "[{\"Laser3Filter\": {\"languages\": [\"${SRC}\", \"${TRG}\"]}, \"module\": \"laser_similarity\"}]"

echo "###### Done

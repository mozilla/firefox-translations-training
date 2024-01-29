#!/bin/bash
##
# Evaluate a quantized model on CPU. This utilizes quantized models that are only
# supported in the the "browsermt" variant of the bergamot translator:
#
# https://github.com/browsermt/bergamot-translator/
#
# This eval step also requires a lexical shortlist.
#
# Kinds:
#  taskcluster/kinds/evaluate-quantized/kind.yml
#
# Example usage:
#
# eval-quantized.sh \
#   $MOZ_FETCHES_DIR/model.intgemm.alphas.bin              `# model_path` \
#   $MOZ_FETCHES_DIR/lex.s2t.pruned                        `# shortlist` \
#   $MOZ_FETCHES_DIR/wmt09                                 `# dataset_prefix` \
#   $MOZ_FETCHES_DIR/vocab.spm                             `# vocab` \
#   $TASK_WORKDIR/artifacts/wmt09                          `# artifacts_prefix` \
#   $TASK_WORKDIR/$VCS_PATH/pipeline/quantize/decoder.yml   # decoder_config

set -x
set -euo pipefail

echo "###### Evaluation of a quantized model"

if [[ -z "${BMT_MARIAN:-}" ]]; then
    echo "Error: The BMT_MARIAN environment variable was not provided. This is required as"
    echo 'the path to the "browsermt" variant of the Marian binary.'
    echo "https://github.com/browsermt/bergamot-translator/"
    exit 1
fi

if [[ -z "${TRG:-}" ]]; then
    echo "Error: The TRG environment variable was not provided."
    exit 1
fi

if [[ -z "${SRC:-}" ]]; then
    echo "Error: The SRC environment variable was not provided."
    exit 1
fi

model_path=$1
shortlist=$2
dataset_prefix=$3
vocab=$4
artifacts_prefix=$5
decoder_config=$6

cd "$(dirname "${0}")"

bash eval.sh \
      "${artifacts_prefix}" \
      "${dataset_prefix}" \
      "${SRC}" \
      "${TRG}" \
      "${BMT_MARIAN}" \
      "${decoder_config}" \
      --models "${model_path}" \
      --vocabs "${vocab}" "${vocab}" \
      `# The second parameter to the shortlist arguments specifies whether or not the` \
      `# shortlist is validated by marian when loaded into memory.` \
      --shortlist "${shortlist}" false \
      --int8shiftAlphaAll

echo "###### Done: Evaluation of a quantized model"

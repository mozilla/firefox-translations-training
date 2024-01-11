#!/bin/bash
##
# Evaluate a trained model with both the BLEU and chrF metrics.
#
# Kinds:
#   taskcluster/kinds/evaluate/kind.yml
#   taskcluster/kinds/evaluate-quantized/kind.yml
#   taskcluster/kinds/evaluate-teacher-ensemble/kind.yml
#
# Example usage:
#
#   eval.sh \
#     $TASK_WORKDIR/artifacts/wmt09                              `# artifacts_prefix` \
#     $MOZ_FETCHES_DIR/wmt09                                     `# dataset_prefix`   \
#     en                                                         `# src`              \
#     ru                                                         `# trg`              \
#     $MARIAN                                                    `# marian`           \
#     $MOZ_FETCHES_DIR/final.model.npz.best-chrf.npz.decoder.yml `# decoder_config`   \
#     `# Additional arguments:`                                                       \
#       -w $WORSPACE \
#       --devices $GPUS \
#       --models $MOZ_FETCHES_DIR/final.model.npz.best-chrf.npz
#
# Artifacts:
#
# For instance for a artifacts_prefix of: `artifacts/wmt09`:
#
#   artifacts
#   ├── wmt09.en             The source sentences
#   ├── wmt09.hu             The target output
#   ├── wmt09.hu.ref         The original target sentences
#   ├── wmt09.log            The Marian log
#   └── wmt09.metrics        The BLEU and chrF score

set -x
set -euo pipefail

echo "###### Evaluation of a model"

# The location where the translated results will be saved. See the artifacts documentation
# above for more details.
artifacts_prefix=$1
# The evaluation datasets prefix, used in the form.
#
# For instance for a value of: `fetches/wmt09`:
#   fetches
#   ├── wmt09.en.zst
#   └── wmt09.hu.zst
dataset_prefix=$2
# The source language, e.g "en".
src=$3
# The target language, e.g "hu".
trg=$4
# The path the to marian binaries.
marian=$5
# The marian yaml config for the model.
decoder_config=$6
# Additional arguments to pass to marian.
marian_args=( "${@:7}" )


COMPRESSION_CMD="${COMPRESSION_CMD:-pigz}"
ARTIFACT_EXT="${ARTIFACT_EXT:-gz}"


# Ensure that the artifacts directory exists.
mkdir -p "$(dirname "${artifacts_prefix}")"

echo "### Evaluating dataset: ${dataset_prefix}, pair: ${src}-${trg}, Results prefix: ${artifacts_prefix}"

# Save the original target sentences to the artifacts.
${COMPRESSION_CMD} -dc "${dataset_prefix}.${trg}.${ARTIFACT_EXT}" > "${artifacts_prefix}.${trg}.ref"

${COMPRESSION_CMD} -dc "${dataset_prefix}.${src}.${ARTIFACT_EXT}" |
  tee "${artifacts_prefix}.${src}" |
  "${marian}"/marian-decoder \
    --config "${decoder_config}" \
    --quiet \
    --quiet-translation \
    --log "${artifacts_prefix}.log" \
    "${marian_args[@]}" |
  tee "${artifacts_prefix}.${trg}" |
  sacrebleu "${artifacts_prefix}.${trg}.ref" \
    --detail \
    --format text \
    --score-only \
    --language-pair "${src}-${trg}" \
    --metrics bleu chrf  |
  tee "${artifacts_prefix}.metrics"

echo "###### Done: Evaluation of a model"

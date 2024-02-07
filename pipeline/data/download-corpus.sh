#!/bin/bash
##
# Downloads parallel dataset
#

set -x
set -euo pipefail

[[ -z "${SRC}" ]] && echo "SRC is empty"
[[ -z "${TRG}" ]] && echo "TRG is empty"


dataset=$1
output_prefix=$2

echo "###### Downloading dataset ${dataset}"

cd "$(dirname "${0}")"

dir=$(dirname "${output_prefix}")
mkdir -p "${dir}"

name=${dataset#*_}
type=${dataset%%_*}

# Choose either the .sh or .py script.
if [[ -f "importers/corpus/${type}.py" ]]; then
  script="python importers/corpus/${type}.py"
else
  script="bash importers/corpus/${type}.sh"
fi

${script} "${SRC}" "${TRG}" "${output_prefix}" "${name}"

echo "###### Done: Downloading dataset ${dataset}"

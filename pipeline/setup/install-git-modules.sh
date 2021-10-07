#!/bin/bash
##
# Installs git modules
#

set -x
set -euo pipefail

echo "### Updating git submodules"
git submodule update --init --recursive


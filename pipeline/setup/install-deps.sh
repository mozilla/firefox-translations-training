#!/bin/bash
##
# Installs system dependencies
#
# Usage:
#   bash install-deps.sh
#

set -x
set -euo pipefail

echo "######### Installing dependencies"

echo "### Updating git submodules"
git submodule update --init --recursive

echo "### Installing extra dependencies"
sudo apt-get install -y pigz htop wget unzip parallel

echo "### Installing marian dependencies"
apt-get install -y build-essential libboost-system-dev libprotobuf10 \
  protobuf-compiler libprotobuf-dev openssl libssl-dev libgoogle-perftools-dev


echo "######### Done: Installing dependencies"

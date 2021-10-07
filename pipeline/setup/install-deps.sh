#!/bin/bash
##
# Installs system dependencies
#

set -x
set -euo pipefail

echo "######### Installing dependencies"

apt-get update

echo "### Installing extra dependencies"
apt-get install -y pigz htop wget unzip parallel bc

echo "### Installing marian dependencies"
apt-get install -y build-essential libboost-system-dev libprotobuf10 \
  protobuf-compiler libprotobuf-dev openssl libssl-dev libgoogle-perftools-dev

echo "### Installing fast_align dependencies "
apt-get install -y libgoogle-perftools-dev libsparsehash-dev libboost-all-dev

echo "######### Done: Installing dependencies"

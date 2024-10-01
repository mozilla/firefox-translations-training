#!/bin/bash
set -e

# Run script from the context of inference directory
cd "$(dirname $0)/.."

# Ensure script is running within docker
./scripts/detect-docker.sh inference-clean

# List of directories to clean
dirs=("build-local" "build-wasm" "emsdk")

# Flag to track if any directories were cleaned
cleaned=false

# Check and remove directories
for dir in "${dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo "Removing $dir..."
        rm -rf "$dir"
        cleaned=true
    fi
done

# If no directories were cleaned, print a message
if [ "$cleaned" = false ]; then
    echo "Nothing to clean"
fi


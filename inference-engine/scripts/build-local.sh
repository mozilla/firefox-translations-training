#!/bin/bash
set -e

# Run script from the context of inference-engine directory
cd "$(dirname $0)/.."

# Ensure script is running within docker
./scripts/detect-docker.sh inference-engine-build

# Return the number of available CPUs, or default to 1 if nproc is unavailable.
detect_cpus() {
  if command -v nproc >/dev/null 2>&1; then
    nproc
  else
    echo 1
  fi
}

if [ ! -d "build-local" ]; then
  echo "Creating build-local directory..."
  mkdir build-local
else
  echo "build-local directory already exists. Skipping creation."
fi

cd build-local || exit

echo "Running cmake for build-local..."
cmake ../

# Run make using the detected number of CPUs
CPUS=$(detect_cpus)
echo "Running make for build-local with $CPUS CPUs..."
make -j ${CPUS}


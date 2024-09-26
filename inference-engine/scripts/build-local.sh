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

# Parse command-line arguments for the --test flag
COMPILE_TESTS=OFF
while [[ "$#" -gt 0 ]]; do
  case $1 in
    "--test") COMPILE_TESTS=ON ;;
    *) echo "Unknown parameter passed: $1"; exit 1 ;;
  esac
  shift
done

if [ ! -d "build-local" ]; then
  echo "Creating build-local directory..."
  mkdir build-local
else
  echo "build-local directory already exists. Skipping creation."
fi

cd build-local || exit

# Run cmake with optional COMPILE_TESTS flag
echo "Running cmake for build-local..."
if [ "$COMPILE_TESTS" = "ON" ]; then
  cmake ../ -DCOMPILE_TESTS=ON
else
  cmake ../
fi

# Run make using the detected number of CPUs
CPUS=$(detect_cpus)
echo "Running make for build-local with $CPUS CPUs..."
make -j ${CPUS}


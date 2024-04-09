#!/bin/bash
set -x

# This file contains boilerplate setup for local Docker commands.

# Containers are usually multi-architecture, and so an AMD machine such as the new
# M1 processers for macbook will choose AMD over x86. The translations C++ code doesn't
# usually work nicely with AMD, so the Docker containers need to be forced to use x86_64
# architectures. This is quite slow, but will still be a usable Docker container.
if [ $(uname -m) == 'arm64' ]; then
  echo "Overriding the arm64 architecture as amd64.";
  export DOCKER_DEFAULT_PLATFORM=linux/amd64;
fi

#!/bin/bash
set -x

# This file contains boilerplate setup for local Docker commands.

# This is a mitigation to guard against build failures with the new
# Apple ARM processors as poetry can change `uname -m` output to x86_64
# if it runs under Rosetta
if [ -n "$VIRTUAL_ENV" ]; then
  echo "Error: Virtual environment detected. Exit the poetry shell.";
  exit 1;
fi

# Containers are usually multi-architecture, and so an AMD machine such as the new
# M1 processers for macbook will choose AMD over x86. The translations C++ code doesn't
# usually work nicely with AMD, so the Docker containers need to be forced to use x86_64
# architectures. This is quite slow, but will still be a usable Docker container.
if [ $(uname -m) == 'arm64' ]; then
  echo "Overriding the arm64 architecture as amd64.";
  export DOCKER_DEFAULT_PLATFORM=linux/amd64;
fi

#!/bin/bash
set -x

# Build the local docker image, see the Taskfile.yml for usage.

source utils/tasks/docker-setup.sh

DOCKER_IMAGE_PARENT=ftt-base taskgraph build-image base --tag ftt-base
taskgraph build-image test --tag ftt-test

docker build \
  --build-arg DOCKER_IMAGE_PARENT=ftt-test \
  --file docker/Dockerfile \
  --tag ftt-local .

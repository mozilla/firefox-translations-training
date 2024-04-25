#!/bin/bash
set -x

# Build the local docker image, see the Taskfile.yml for usage.

source utils/tasks/docker-setup.sh

docker build \
  --file taskcluster/docker/base/Dockerfile \
  --tag ftt-base .

docker build \
  --build-arg DOCKER_IMAGE_PARENT=ftt-base \
  --file taskcluster/docker/test/Dockerfile \
  --tag ftt-test .

docker build \
  --build-arg DOCKER_IMAGE_PARENT=ftt-test \
  --file docker/Dockerfile \
  --tag ftt-local .

#!/bin/bash
set -x

# Build the local docker image, see the Taskfile.yml for usage.

source utils/tasks/docker-setup.sh

docker build \
  --file taskcluster/docker/base/Dockerfile \
  --tag translations-base .

docker build \
  --build-arg DOCKER_IMAGE_PARENT=translations-base \
  --file taskcluster/docker/test/Dockerfile \
  --tag translations-test .

docker build \
  --build-arg DOCKER_IMAGE_PARENT=translations-test \
  --file docker/Dockerfile \
  --tag translations-local .

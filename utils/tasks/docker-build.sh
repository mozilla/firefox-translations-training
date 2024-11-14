#!/bin/bash
set -x

# Build the local docker image, see the Taskfile.yml for usage.

source utils/tasks/docker-setup.sh

DOCKER_BASE_PATH=taskcluster/docker/base
DOCKER_TEST_PATH=taskcluster/docker/test

docker build \
  --file "$DOCKER_BASE_PATH/Dockerfile" \
  --tag translations-base $DOCKER_BASE_PATH

docker build \
  --build-arg DOCKER_IMAGE_PARENT=translations-base \
  --file "$DOCKER_TEST_PATH/Dockerfile" \
  --tag translations-test $DOCKER_TEST_PATH

docker build \
  --build-arg DOCKER_IMAGE_PARENT=translations-test \
  --file "docker/Dockerfile" \
  --tag translations-local .

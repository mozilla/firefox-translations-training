#!/bin/bash
set -x
set -euo pipefail

# Build the local docker image, see the Taskfile.yml for usage.

source utils/tasks/docker-setup.sh
# taskgraph build-image base --tag ftt-base

docker build \
  --file taskcluster/docker/base/Dockerfile \
  --tag ftt-base .

build_test_docker() {
  # The docker image in CI uses special "include directives" through a taskgraph feature.
  # This isn't available locally, so rewrite the Dockerfile to apply the `topsrcdir` argument.
  #
  # https://taskcluster-taskgraph.readthedocs.io/en/6.0.0/howto/docker.html
  #
  # These can be applied with:
  #
  #    DOCKER_IMAGE_PARENT=ftt-base taskgraph build-image test --tag ftt-test
  #
  # And changing the `ARG DOCKER_IMAGE_PARENT` to `# %ARG DOCKER_IMAGE_PARENT` but then
  # it breaks when run in CI.
  #
  # See also: https://github.com/taskcluster/taskgraph/issues/582

  test_dockerfile="taskcluster/docker/test/Dockerfile"
  test_dockerfile_fixed="${test_dockerfile}.fixed"

  # Remove the "topsrcdir"
  # e.g.
  #   ADD topsrcdir/pipeline/quantize/requirements/quantize.txt      requirements
  #   ADD pipeline/quantize/requirements/quantize.txt      requirements
  sed 's/^ADD topsrcdir\//ADD /' "${test_dockerfile}" > "${test_dockerfile_fixed}"

  docker build \
      --build-arg DOCKER_IMAGE_PARENT=ftt-base \
      --file "${test_dockerfile_fixed}" \
      --tag ftt-test .
}

build_test_docker

docker build \
  --build-arg DOCKER_IMAGE_PARENT=ftt-test \
  --file docker/Dockerfile \
  --tag ftt-local .

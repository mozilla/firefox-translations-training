#!/bin/bash
set -x

# Run the local docker image, see the Taskfile.yml for usage.

echo 'Running docker run'

source utils/tasks/docker-setup.sh

echo 'Running docker run'

docker run \
  --interactive \
  --tty \
  --rm \
  --volume $(pwd):/builds/worker/checkouts \
  --workdir /builds/worker/checkouts \
  ftt-local "$@"

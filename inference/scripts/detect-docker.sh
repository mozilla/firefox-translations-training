#!/bin/bash

help_task=$1

if [ "${IS_DOCKER}" != "1" ]; then
  if [ "${ALLOW_RUN_ON_HOST}" != "1" ]; then
    echo >&2
    echo "Error: This script needs to be run inside Docker, or you must set ALLOW_RUN_ON_HOST=1." >&2
    echo >&2
    if [ -n "${help_task}" ]; then
      echo " Help: To run this script directly in docker, run: task docker-run -- task ${help_task}" >&2
    fi
    echo " Help: To enter docker, run: task docker" >&2
    echo
    exit 1
  else
    echo >&2
    echo "ALLOW_RUN_ON_HOST is set to 1. Continuing..." >&2
  fi
fi

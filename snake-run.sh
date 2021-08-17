#!/bin/bash

source config.sh

snakemake \
  --use-conda \
  --cores all \
  --wms-monitor http://127.0.0.1:5000 \
  "$@"
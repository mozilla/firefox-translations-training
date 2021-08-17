#!/bin/bash

source config.sh
snakemake --use-conda --cores all "$@"
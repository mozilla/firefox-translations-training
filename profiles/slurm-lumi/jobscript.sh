#!/bin/bash -x
# properties = {properties}

#parse properties json and get log file name
log_file=$(echo '{properties}' | jq -r .log[0])

mkdir -p $(dirname $log_file)

rocm-smi --showenergycounter > $log_file.gpu

{exec_job} && rocm-smi --showenergycounter >> $log_file.gpu


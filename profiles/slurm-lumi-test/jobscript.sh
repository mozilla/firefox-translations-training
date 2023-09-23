#!/bin/bash -x
# properties = {properties}

#parse properties json and get log file name
log_file=$(echo '{properties}' | jq -r .log[0])
gpu=$(echo '{properties}' | jq -r .resources.gpu)

mkdir -p $(dirname $log_file)

if [ $gpu != "null" ] && [ $gpu != "0" ]; then
  #this will add the header row for the csv file, it will be removed for later log lines
  rocm-smi --csv --showuse --showmemuse --showenergycounter 2> /dev/null | head -1 > $log_file.gpu
  while true; do
    rocm-smi --csv --showuse --showmemuse --showenergycounter 2> /dev/null | \
    grep -v "device" | xargs -I {{}} echo -e "$(date "+%Y-%m-%d_%H:%M:%S")\t{{}}" >> $log_file.gpu; sleep 10;
  done &
  rocmloop_pid=$!
fi

{exec_job} 

if [ -z $rocmloop_pid ]; then 
    kill $rocmloop_pid
fi

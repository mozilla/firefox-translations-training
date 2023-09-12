#!/bin/bash
set +x
# properties = {properties}

#parse properties json and get log file name
log_file=$(echo '{properties}' | jq -r .log[0])
gpu=$(echo '{properties}' | jq -r .resources.gpu)

export SINGULARITYENV_CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES

if [ $gpu != "null" ] && [ $gpu != "0" ]; then
    nvidia-smi --query-gpu=timestamp,name,pci.bus_id,driver_version,pstate,pcie.link.gen.max,pcie.link.gen.current,temperature.gpu,utilization.gpu,utilization.memory,power.draw,memory.total,memory.free,memory.used --format=csv -l 10 > $log_file.gpu &
    nvidiasmi_pid=$!
    #/appl/soft/ai/bin/gpu-energy
    #monitor_pid=$!
fi

{exec_job}

if [ -z $nvidiasmi_pid ]; then
   kill $nvidiasmi_pid 
fi
if [ -z $monitor_pid ]; then
   kill -SIGUSR1 $monitor_pid 
fi

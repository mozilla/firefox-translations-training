#!/bin/bash
# properties = {properties}

export SINGULARITYENV_CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES

{exec_job}

# for job arrays
exit_status=$?
scancel $SLURM_JOBID
exit ${exec_exit_status}
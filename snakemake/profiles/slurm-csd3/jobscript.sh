#!/bin/bash
# properties = {properties}

export SINGULARITYENV_CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES

if [ ! -z "$SLURM_ARRAY_JOB_ID" ]; then
    trap 'kill "$jobpid"' TERM
    trap 'kill "$jobpid"' INT
    trap 'kill "$jobpid"' USR1

    {exec_job} &
    jobpid=$!

    wait $jobpid
    wait $jobpid
    exit_status=$?

    # Now we interpret the exit status.
    if [ "$exit_status" == 143 ]; then # 143 = 128 + 15 => SIGTERM
        echo "Not done, continue in the next slot"
        exit 0
    else
        if [ "$exit_status" == 0 ]; then
            echo "Completed"
        else
            echo "Failed"
        fi;
        # Either we are finished or training failed so we need to
        # investigate; there's no point in continuing training here.
        echo "Cancelling job array"
        scancel --state=PENDING $SLURM_ARRAY_JOB_ID
        exit $exit_status
    fi
else
    {exec_job}
fi
#!/bin/bash

##
# Train a model.
#

##########################################################################
# Slurm directives; see slurm documentation for what these parameters mean.
# This script can also be run on the commandline outside of slurm.
# In this case, slurm directives are simply ignored.
#
# Slurm directives start with #SBATCH. Do not remove the leading #.
# It's part of the directive. Leading ## comments out the
# respective slurm directive. All of the directives can also be
# supplied on the command line when the slurm job is submitted.
#
# Uncomment and adjust the following to your own account settings. Of
# course, these can also be provided with the sbatch call on the
# command line.
# Your account (-A) and the appropriate slurm partition (-p):
##SBATCH -A <account>
##SBATCH -p <partition>
#
# How many GPUs and nodes do you want to use?
#SBATCH --gres=gpu:4
#SBATCH --nodes=1
# Set the job name so that we can find our jobs more easily in squeue.
#SBATCH -J "marian"
# Send me mail for everything that happens.
#SBATCH --mail-type=ALL
# I prefer a meaningful log file name over the one automatically assigned by
# slurm. This will be placed in the current working directory from which
# the slurm job was submitted.
#SBATCH --output=train-model.log
#
# ---------------------------------------------------------------------------
# Handling of time slot limitations.
# ---------------------------------------------------------------------------
#
# Time slot limits imposed by slurm may not be enough to complete training.
# Luckily, Marian will by default save its current training state if it is
# terminated with SIGKILL (signal #15). The approach we take is as follows.
# 1. We schedule the training as an array of slurm jobs that run consecutively.
# 2. We run marian in the background and keep track of its process id.
# 3. We ask slurm to send us SIGUSR1 a few minutes ahead of the time limit.
# 4. We install a signal handler in this script to handle that signal.
# 5. The signal handler sends SIGTERM to the marian process.
# 6. We wait for marian to finish and interpret its exit status.
#    - exit status 0: training finished normally. We cancel the rest of the
#      slurm job array.
#    - exit status 143 (= 128 + 15): marian received SIGTERM, saved its
#      state of training and can be resumed in the next job in the job array.
#    - any other exit status: something went wrong and we need to investigate.
#      There's no point in continuing training, so we cancel the job array.
#
# Maximum time allowed on CSD3 is 36 hours. Not sure if this needs to
# be set, but helpful for debugging. Notice that a new marian training
# run needs to have finished a bit of training (so that there is
# something to save), or it may crash while trying to do so. This
# might need fixing in the marian code.
##SBATCH --time=36:00:00
#
# Send me signal SIGUSR1 five minutes before the slot time is up.
#SBATCH --signal=B:USR1@300
#
# Schedule a series of 20 consecutive (%1) slots. This is probably
# overkill in terms of slot allocation, but we cancel slots if not
# needed anyway, so there's no harm in setting this to a high value.
#SBATCH --array=1-20%1
###########################################################################

# START OF THE ACTUAL SCRIPT
set -x
set -euo pipefail

this_script=$0

# Set up signal handlers.
signal_handler() {
    echo "Process $$ ($this_script) received signal $1."
    echo "Sending SIGTERM to process $marian_pid."
    kill $marian_pid
}
trap "signal_handler SIGERM" TERM
trap "signal_handler SIGINT" INT
trap "signal_handler SIGUSR1" USR1

# Now we start the marian process in the background.

echo "###### Training a model"

model_type=$1
training_type=$2
src=$3
trg=$4
train_set_prefix=$5
valid_set_prefix=$6
model_dir=$7
vocab=$8
extra_params=( "${@:9}" )

test -v GPUS
test -v MARIAN
test -v WORKSPACE

cd "$(dirname "${0}")"
mkdir -p "${model_dir}/tmp"

echo "### Training ${model_dir}"

# if doesn't fit in RAM, remove --shuffle-in-ram and add --shuffle batches

"${MARIAN}/marian" \
  --model "${model_dir}/model.npz" \
  -c "configs/model/${model_type}.yml" "configs/training/${model_type}.${training_type}.yml" \
  --train-sets "${train_set_prefix}".{"${src}","${trg}"}.gz \
  -T "${model_dir}/tmp" \
  --shuffle-in-ram \
  --vocabs "${vocab}" "${vocab}" \
  -w "${WORKSPACE}" \
  --devices ${GPUS} \
  --sharding local \
  --sync-sgd \
  --valid-metrics chrf ce-mean-words bleu-detok \
  --valid-sets "${valid_set_prefix}".{"${src}","${trg}"}.gz \
  --valid-translation-output "${model_dir}/devset.out" \
  --quiet-translation \
  --overwrite \
  --keep-best \
  --log "${model_dir}/train.log" \
  --valid-log "${model_dir}/valid.log" \
  "${extra_params[@]}" &

# keep track of the process ID of the child
marian_pid=$!

wait $marian_pid
wait $marian_pid # Yes, twice. See explanation below.
marian_exit_status=$?
# Wait stops waiting under two conditions.
# 1. The process being waited for finishes. In that case, $? is its exit status.
# 2. A signal handler returns. In that case, $? is 128 plus the signal number.
# A second wait sets does no harm in the first case and sets $? correctly in the
# second.

# Now we interpret the exit status.
if [ "$marian_exit_status" == 143 ]; then # 143 = 128 + 15 => SIGTERM
    echo "### Model training was interrupted: ${model_dir}"
    echo "###### Not done: Training a model"
    # Do not cancel the job array! We want to continue in the next slot
else
    if [ "$marian_exit_status" == 0 ]; then
        echo "### Model training is completed: ${model_dir}"
        echo "###### Done: Training a model"
    else
        echo "### Model training failed: ${model_dir}"
        echo "###### Not done: Training a model"
    fi;
    if [[ "${SLURM_JOBID:-''}" != "" ]] ; then
        # Either we are finished or training failed so we need to
        # investigate; there's no point in continuing training here.
        scancel $SLURM_JOBID
    fi
fi
exit $marian_exit_status

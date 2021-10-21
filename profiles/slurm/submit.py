#!/usr/bin/env python3
import re
import sys
import subprocess as sp
import os

from snakemake.utils import read_job_properties
from snakemake.logging import logger

# todo: move to another config
MULTI_GPU_PARTITION = 'pascal'
CPU_PARTITION = 'skylake'
SINGLE_GPU_PARTITION = 'pascal'
CPU_ACCOUNT = 'T2-CS119-CPU'
GPU_ACCOUNT = 'T2-CS119-GPU'

jobscript = sys.argv[-1]
job_properties = read_job_properties(jobscript)

options = []

if job_properties["type"] == 'single':
    name = job_properties['rule']
elif job_properties["type"] == 'group':
    name = job_properties['groupid']
else:
    raise NotImplementedError(f"Don't know what to do with job_properties['type']=={job_properties['type']}")

options += ['--job-name', name]

partition = CPU_PARTITION
account = CPU_ACCOUNT

if "resources" in job_properties:
    resources = job_properties["resources"]

    if 'gpu' in resources:
        num_gpu = str(resources['gpu'])
        options += [f'--gres=gpu:{num_gpu}']

        account = GPU_ACCOUNT

        if num_gpu == '1':
            partition = SINGLE_GPU_PARTITION
        else:
            partition = MULTI_GPU_PARTITION

        cuda_dir = os.getenv('CUDA_DIR')
        if cuda_dir:
            options += ['--export', f'ALL,SINGULARITY_BIND="{cuda_dir}"']

    if 'mem_mb' in resources:
        memory = str(resources['mem_mb'])
        options += [f'--mem={memory}']

options += ['-p', partition]
options += ['-A', account]
options += ['--nodes=1']

if "threads" in job_properties:
    options += ["--cpus-per-task", str(job_properties["threads"])]

try:
    cmd = ["sbatch"] + ["--parsable"] + options + [jobscript]
    logger.debug(f'Running command: {cmd}')
    res = sp.check_output(cmd)
except sp.CalledProcessError as e:
    raise e
# Get jobid
res = res.decode()
try:
    jobid = re.search(r"(\d+)", res).group(1)
except Exception as e:
    raise e

print(jobid)

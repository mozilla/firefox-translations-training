#!/usr/bin/env python3
import re
import sys
import subprocess as sp
import os

from snakemake.utils import read_job_properties

MULTI_GPU_PARTITION = 'p1'
CPU_PARTITION = 'p2'
SINGLE_GPU_PARTITION = 'p3'

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
if "resources" in job_properties:
    resources = job_properties["resources"]

    if 'gpu' in resources:
        num_gpu = str(resources['gpu'])
        options += [f'--gres=gpu:{num_gpu}']

        if num_gpu == '1':
            partition = SINGLE_GPU_PARTITION
        else:
            partition = MULTI_GPU_PARTITION

        cuda_dir = os.getenv('CUDA_DIR')
        if cuda_dir:
            options += ['--export', f'ALL,SINGULARITY_BIND="{cuda_dir}"']

options += ['-p', partition]

if "threads" in job_properties:
    options += ["--cpus-per-task", str(job_properties["threads"])]

try:
    cmd = ["sbatch"] + ["--parsable"] + options + [jobscript]
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

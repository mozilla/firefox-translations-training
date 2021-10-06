#!/usr/bin/env python3
import re
import sys
import subprocess as sp

from snakemake.utils import read_job_properties

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

if "resources" in job_properties:
    resources = job_properties["resources"]

    num_gpu = resources.get('gpu') or '0'
    options += ['--gpus-per-node', str(num_gpu)]

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

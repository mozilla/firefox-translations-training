#!/usr/bin/env python3
import re
import sys
import subprocess as sp

from snakemake.utils import read_job_properties

jobscript = sys.argv[-1]
job_properties = read_job_properties(jobscript)

options = []

name = job_properties.get("rule")
options += ['--job-name', name]

if "resources" in job_properties:
    resources = job_properties["resources"]

    num_gpu = str(resources.get('gpu')) or '0'
    options += ['--gpus-per-node', num_gpu]

    if "threads" in job_properties:
        options += ["--cpus-per-task", job_properties["threads"]]

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

#!/usr/bin/env python3
import os
import sys
import argparse
import subprocess

from snakemake.utils import read_job_properties


jobscript = sys.argv[-1]
job_properties = read_job_properties(jobscript)


request = '[]' # cpu only
if "resources" in job_properties:
    resources = job_properties["resources"]

    if 'gpu' in resources:
        num = resources['gpu']
        # todo: find available models
        request = f'[{num}:txp]'

name=job_properties.get("rule")
cmd = f'pit run snakemake-{name} {request} -e "{jobscript}"'

try:
    res = subprocess.run(cmd, check=True, shell=True, stdout=subprocess.PIPE)
except subprocess.CalledProcessError as e:
    raise e

res = res.stdout.decode()
job_id=res[res.find('=> job number:'):].strip()
print(job_id)
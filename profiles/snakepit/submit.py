#!/usr/bin/env python3
import os
import sys
import argparse
import subprocess

from snakemake.utils import read_job_properties

jobscript = sys.argv[-1]
job_properties = read_job_properties(jobscript)

request = '[]'  # cpu only
if "resources" in job_properties:
    resources = job_properties["resources"]

    if 'gpu' in resources:
        num = resources['gpu']
        # todo: find available models
        request = f'[{num}:txp]'

name = job_properties.get("rule")
cmd = f'''
        unset http_proxy 
	    unset HTTP_PROXY 
	    mkdir -p empty 
	    cd empty 
	    pit run snakemake-{name} {request} -e "bash {jobscript}"'''

try:
    res = subprocess.run(cmd, check=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
except subprocess.CalledProcessError as e:
    raise e

res = res.stdout.decode()
number_line = '=> job number:'
job_id = res[res.find(number_line) + len(number_line):].strip()
print(job_id)

#!/usr/bin/env python3


import sys
import subprocess

job_id = sys.argv[1]

try:
    res = subprocess.run('pit show job:{}'.format(job_id),
                         check=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT,
                         shell=True)

    info = res.stdout.decode()

    if 'FIN' in info:
        if 'Status code: 0' in info:
            print("success")
        else:
            print("failed")
    else:
        print("running")

except (subprocess.CalledProcessError, IndexError, KeyboardInterrupt) as e:
    print("failed")

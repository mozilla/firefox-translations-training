#!/usr/bin/env python3
import re
import subprocess as sp
import shlex
import sys
import time
import logging

logger = logging.getLogger("__name__")

STATUS_ATTEMPTS = 20

jobid = sys.argv[1]

for i in range(STATUS_ATTEMPTS):
    try:
        sacct_res = sp.check_output(shlex.split(f"sacct -P -b -j {jobid} -n"))
        res = {
            x.split("|")[0]: x.split("|")[1]
            for x in sacct_res.decode().strip().split("\n")
        }
        # regular execution
        if jobid in res:
            status = res[jobid]
        # job array
        else:
            all_steps = sorted([(k, v) for k, v in res.items() if not k.endswith('batch') and '[' not in k],
                               key=lambda x: x[0])
            statuses = {v for _, v in all_steps}
            if "COMPLETED" in statuses:
                status = "COMPLETED"
            elif "FAILED" in statuses:
                status = "FAILED"
            else:
                status = all_steps[-1][1]
        break
    except sp.CalledProcessError as e:
        logger.error("sacct process error")
        logger.error(e)
    except IndexError as e:
        logger.error(e)
        pass
    # Try getting job with scontrol instead in case sacct is misconfigured
    try:
        sctrl_res = sp.check_output(
            shlex.split(f"scontrol -o show job {jobid}")
        )
        statuses = [re.search(r"JobState=(\w+)", line).group(1)
                    for line in sctrl_res.decode().split('\n') if line != ""]
        if "COMPLETED" in statuses:
            status = "COMPLETED"
        elif "FAILED" in statuses:
            status = "FAILED"
        else:
            status = statuses[0]
        break
    except sp.CalledProcessError as e:
        logger.error("scontrol process error")
        logger.error(e)
        if i >= STATUS_ATTEMPTS - 1:
            print("failed")
            exit(0)
        else:
            time.sleep(1)


if status == "BOOT_FAIL":
    print("failed")
elif status == "OUT_OF_MEMORY":
    print("failed")
elif status.startswith("CANCELLED"):
    print("failed")
elif status == "COMPLETED":
    print("success")
elif status == "DEADLINE":
    print("failed")
elif status == "FAILED":
    print("failed")
elif status == "NODE_FAIL":
    print("failed")
elif status == "PREEMPTED":
    print("failed")
elif status == "TIMEOUT":
    print("failed")
elif status == "SUSPENDED":
    print("running")
else:
    print("running")


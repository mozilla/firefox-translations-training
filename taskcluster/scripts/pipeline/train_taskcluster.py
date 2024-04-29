#!/usr/bin/env python3

import os.path
import subprocess
import sys

TRAINING_SCRIPT = os.path.join(os.path.dirname(__file__), "train-taskcluster.sh")


def main(args):
    subprocess.run([TRAINING_SCRIPT, *args], check=True)


if __name__ == "__main__":
    main(sys.argv[1:])

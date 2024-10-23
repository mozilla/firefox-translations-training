#!/usr/bin/env python3

import argparse
import subprocess
import os
import sys


def get_args():
    parser = argparse.ArgumentParser(description="Run the local docker image.")

    parser.add_argument(
        "--volume",
        action="append",
        help="Specify additional volume(s) to mount in the Docker container.",
        metavar="VOLUME",
    )

    args, other_args = parser.parse_known_args()
    args.other_args = other_args

    return args


def main():
    args = get_args()

    docker_command = [
        "docker",
        "run",
        "--interactive",
        "--tty",
        "--rm",
        "--volume",
        f"{os.getcwd()}:/builds/worker/checkouts",
        "--workdir",
        "/builds/worker/checkouts",
    ]

    # Add additional volumes if provided
    if args.volume:
        for volume in args.volume:
            docker_command.extend(["--volume", volume])

    # Specify the Docker image
    docker_command.append("ftt-local")

    # Append any additional args
    if args.other_args:
        docker_command.extend(args.other_args)

    print("Executing command:", " ".join(docker_command))
    result = subprocess.run(docker_command, check=False)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()

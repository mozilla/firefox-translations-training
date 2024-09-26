# From
import argparse
import hashlib
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

FIXTURES_PATH = os.path.dirname(os.path.abspath(__file__))
ROOT_PATH = os.path.abspath(os.path.join(FIXTURES_PATH, "../.."))
DATA_PATH = os.path.abspath(os.path.join(ROOT_PATH, "data"))
PIPELINE = os.path.abspath(os.path.join(ROOT_PATH, "data"))


def get_python_dirs(requirements: Optional[str], data_path=DATA_PATH) -> Optional[Tuple[str, str]]:
    """
    Creates a virtual environment for each requirements file that a task needs. The virtual
    environment is hashed based on the requirements file contents, and the system details. This
    way a virtual environment will be re-used between docker environments.
    """
    if not requirements:
        return None

    system_details = "-".join(
        [
            platform.system(),  # Linux
            platform.machine(),  # aarch64
            platform.release(),  # 5.15.49-linuxkit-pr
        ]
    )

    # Create a hash based on files and contents that would invalidate the python library.
    md5 = hashlib.md5()
    hash_file(md5, requirements)
    md5.update(system_details.encode("utf-8"))
    if os.environ.get("IS_DOCKER"):
        hash_file(md5, os.path.join(ROOT_PATH, "docker/Dockerfile"))
    hash = md5.hexdigest()

    requirements_stem = Path(requirements).stem
    environment = "docker" if os.environ.get("IS_DOCKER") else "native"
    venv_dir = os.path.abspath(
        os.path.join(data_path, "task-venvs", f"{environment}-{requirements_stem}-{hash}")
    )
    python_bin_dir = os.path.join(venv_dir, "bin")
    python_bin = os.path.join(python_bin_dir, "python3")

    # Create the venv only if it doesn't exist.
    if not os.path.exists(venv_dir):
        try:
            print(f"{venv_dir} does not exist")
            print("Creating virtual environment for", requirements)
            subprocess.check_call(
                # Give the virtual environment access to the system site packages, as these
                # are installed via docker.
                ["python3", "-m", "venv", "--system-site-packages", venv_dir],
            )

            print("Installing setuptools", requirements)
            subprocess.check_call(
                [
                    python_bin,
                    "-m",
                    "pip",
                    "install",
                    "--no-cache-dir",
                    "--timeout",
                    "600",
                    "--upgrade",
                    "setuptools",
                    "pip",
                ]  # fmt: skip,
            )

            print("Installing", requirements)
            subprocess.check_call(
                [
                    python_bin,
                    "-m",
                    "pip",
                    "install",
                    "--no-cache-dir",
                    "--timeout",
                    "600",
                    "-r",
                    requirements,
                ],
            )
        except Exception as exception:
            print("Removing the venv due to an error in its creation.")
            shutil.rmtree(venv_dir)
            raise exception
    print(f"Using virtual environment {venv_dir}")

    return python_bin_dir, venv_dir


def hash_file(hash: any, path: str):
    """
    Hash the contents of a file.
    """
    print("hashing", path)
    with open(path, "rb") as f:
        while chunk := f.read(4096):
            hash.update(chunk)


if __name__ == "__main__":
    """
    If called as a command line tool, install a specific venv.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--requirements", type=str, help="The requirements file")
    parser.add_argument("--output", type=str, help="The data folder")

    args = parser.parse_args()
    get_python_dirs(args.requirements, data_path=args.output)

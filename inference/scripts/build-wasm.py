#!/usr/bin/env python3
import argparse
import multiprocessing
import os
import shutil
import subprocess
from collections import namedtuple

SCRIPTS_PATH = os.path.realpath(os.path.dirname(__file__))
INFERENCE_PATH = os.path.dirname(SCRIPTS_PATH)
PROJECT_ROOT_PATH = os.path.dirname(INFERENCE_PATH)
BUILD_PATH = os.path.join(INFERENCE_PATH, "build-wasm")
THIRD_PARTY_PATH = os.path.join(INFERENCE_PATH, "3rd_party")
MARIAN_PATH = os.path.join(THIRD_PARTY_PATH, "browsermt-marian-dev")
EMSDK_PATH = os.path.join(THIRD_PARTY_PATH, "emsdk")
EMSDK_ENV_PATH = os.path.join(EMSDK_PATH, "emsdk_env.sh")
WASM_PATH = os.path.join(BUILD_PATH, "bergamot-translator-worker.wasm")
JS_PATH = os.path.join(BUILD_PATH, "bergamot-translator-worker.js")
PATCHES_PATH = os.path.join(INFERENCE_PATH, "patches")
BUILD_DIRECTORY = os.path.join(INFERENCE_PATH, "build-wasm")
GEMM_SCRIPT = os.path.join(INFERENCE_PATH, "wasm", "patch-artifacts-import-gemm-module.sh")
DETECT_DOCKER_SCRIPT = os.path.join(SCRIPTS_PATH, "detect-docker.sh")

# 3.1.47 had an error compiling sentencepiece.
EMSDK_VERSION = "3.1.8"
EMSDK_REVISION = "2346baa7bb44a4a0571cc75f1986ab9aaa35aa03"

patches = [
    (MARIAN_PATH, os.path.join(PATCHES_PATH, "01-marian-fstream-for-macos.patch")),
    (MARIAN_PATH, os.path.join(PATCHES_PATH, "02-marian-allocation.patch")),
]

parser = argparse.ArgumentParser(
    description=__doc__,
    # Preserves whitespace in the help text.
    formatter_class=argparse.RawTextHelpFormatter,
)
parser.add_argument("--clobber", action="store_true", help="Clobber the build artifacts")
parser.add_argument(
    "--debug",
    action="store_true",
    help="Build with debug symbols, useful for profiling",
)

ArgNamespace = namedtuple("ArgNamespace", ["clobber", "debug"])


def ensure_docker():
    """Ensure the script is running inside Docker."""
    subprocess.run(
        [DETECT_DOCKER_SCRIPT, "inference-build-wasm"],
        cwd=INFERENCE_PATH,
        shell=True,
        check=True,
    )


def git_clone_update(name: str, repo_path: str, repo_url: str, revision: str):
    if not os.path.exists(repo_path):
        print(f"\n⬇️ Clone the {name} repo into {repo_path}\n")
        subprocess.check_call(
            ["git", "clone", repo_url],
            cwd=THIRD_PARTY_PATH,
        )

    local_head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_path,
        text=True,
    ).strip()

    def run(command):
        return subprocess.check_call(command, cwd=repo_path)

    if local_head != revision:
        print(f"The head ({local_head}) and revision ({revision}) don't match.")
        print(f"\n🔎 Fetching the latest from {name}.\n")
        run(["git", "fetch", "--recurse-submodules"])

        print(f"🛒 Checking out the revision {revision}")
        run(["git", "checkout", revision])
        run(["git", "submodule", "update", "--init", "--recursive"])


def install_and_activate_emscripten(args: ArgNamespace):
    git_clone_update(
        name="emsdk",
        repo_path=EMSDK_PATH,
        repo_url="https://github.com/emscripten-core/emsdk.git",
        revision=EMSDK_REVISION,
    )

    # Run these commands in the shell so that the configuration is saved.
    def run_shell(command):
        return subprocess.run(command, cwd=EMSDK_PATH, shell=True, check=True)

    print(f"\n🛠️ Installing EMSDK version {EMSDK_VERSION}\n")
    run_shell("./emsdk install " + EMSDK_VERSION)

    print("\n🛠️ Activating emsdk\n")
    run_shell("./emsdk activate " + EMSDK_VERSION)


def to_human_readable(size):
    """Convert sizes to human-readable format"""
    size_in_mb = size / 1048576
    return f"{size_in_mb:.2f}M ({size} bytes)"


def apply_git_patch(repo_path, patch_path):
    print(f"Applying patch {patch_path} to {os.path.basename(repo_path)}")
    subprocess.check_call(["git", "apply", "--reject", patch_path], cwd=PROJECT_ROOT_PATH)


def revert_git_patch(repo_path, patch_path):
    print(f"Reverting patch {patch_path} from {os.path.basename(repo_path)}")
    subprocess.check_call(["git", "apply", "-R", "--reject", patch_path], cwd=PROJECT_ROOT_PATH)


def build_bergamot(args: ArgNamespace):
    if args.clobber and os.path.exists(BUILD_PATH):
        shutil.rmtree(BUILD_PATH)

    if not os.path.exists(BUILD_PATH):
        os.mkdir(BUILD_PATH)

    print("\n🖌️ Applying source code patches\n")
    for repo_path, patch_path in patches:
        apply_git_patch(repo_path, patch_path)

    # These commands require the emsdk environment variables to be set up.
    def run_shell(command):
        if '"' in command or "'" in command:
            raise Exception("This run_shell utility does not support quotes.")

        return subprocess.run(
            # "source" is not available in all shells so explicitly
            f"bash -c 'source {EMSDK_ENV_PATH} && {command}'",
            cwd=BUILD_PATH,
            shell=True,
            check=True,
        )

    try:
        flags = ""
        if args.debug:
            flags = "-DCMAKE_BUILD_TYPE=RelWithDebInfo"

        print("\n🏃 Running CMake for Bergamot\n")
        run_shell(f"emcmake cmake -DCOMPILE_WASM=on -DWORMHOLE=off {flags} {INFERENCE_PATH}")

        print("\n🏃 Building Bergamot with emmake\n")
        run_shell(f"emmake make -j {multiprocessing.cpu_count()}")

        print("\n🪚 Patching Bergamot for gemm support\n")
        subprocess.check_call(["bash", GEMM_SCRIPT, BUILD_PATH])

        print("\n✅ Build complete\n")
        print("  " + JS_PATH)
        print("  " + WASM_PATH)

        # Get the sizes of the build artifacts.
        wasm_size = os.path.getsize(WASM_PATH)
        gzip_size = int(
            subprocess.run(
                f"gzip -c {WASM_PATH} | wc -c",
                check=True,
                shell=True,
                capture_output=True,
            ).stdout.strip()
        )
        print(f"  Uncompressed wasm size: {to_human_readable(wasm_size)}")
        print(f"  Compressed wasm size: {to_human_readable(gzip_size)}")
    finally:
        print("\n🖌️ Reverting the source code patches\n")
        for repo_path, patch_path in patches[::-1]:
            revert_git_patch(repo_path, patch_path)


def main():
    args: ArgNamespace = parser.parse_args()

    if not os.path.exists(THIRD_PARTY_PATH):
        os.mkdir(THIRD_PARTY_PATH)

    ensure_docker()

    install_and_activate_emscripten(args)

    build_bergamot(args)


if __name__ == "__main__":
    main()

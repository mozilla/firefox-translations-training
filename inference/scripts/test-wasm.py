#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys

SCRIPTS_PATH = os.path.realpath(os.path.dirname(__file__))
INFERENCE_PATH = os.path.dirname(SCRIPTS_PATH)
BUILD_PATH = os.path.join(INFERENCE_PATH, "build-wasm")
WASM_PATH = os.path.join(INFERENCE_PATH, "wasm")
WASM_TESTS_PATH = os.path.join(WASM_PATH, "tests")


def main():
    parser = argparse.ArgumentParser(
        description="Test WASM by building and handling artifacts.",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument("--clobber", action="store_true", help="Clobber the build artifacts")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Build with debug symbols, useful for profiling",
    )
    parser.add_argument(
        "-j",
        type=int,
        help="Number of cores to use for building (default: all available cores)",
    )
    args = parser.parse_args()

    build_wasm_script = os.path.join(SCRIPTS_PATH, "build-wasm.py")
    build_command = [sys.executable, build_wasm_script]
    if args.clobber:
        build_command.append("--clobber")
    if args.debug:
        build_command.append("--debug")
    if args.j:
        build_command.extend(["-j", str(args.j)])

    print("\n🚀 Starting build-wasm.py")
    subprocess.run(build_command, check=True)

    print("\n🔧 Installing npm dependencies for WASM JS tests\n")
    subprocess.run(["npm", "install"], cwd=WASM_TESTS_PATH, check=True)

    print("\n📊 Running Translations WASM JS tests\n")
    subprocess.run(["npm", "run", "test"], cwd=WASM_TESTS_PATH, check=True)

    print("\n✅ test-wasm.py completed successfully.\n")


if __name__ == "__main__":
    main()

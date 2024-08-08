import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import time
from pathlib import Path
from subprocess import CompletedProcess
from typing import List, Optional, Union

import zstandard as zstd

from utils.preflight_check import get_taskgraph_parameters, run_taskgraph

FIXTURES_PATH = os.path.dirname(os.path.abspath(__file__))
ROOT_PATH = os.path.abspath(os.path.join(FIXTURES_PATH, "../.."))
DATA_PATH = os.path.abspath(os.path.join(ROOT_PATH, "data"))
TESTS_DATA = os.path.join(DATA_PATH, "tests_data")


en_sample = """The little girl, seeing she had lost one of her pretty shoes, grew angry, and said to the Witch, “Give me back my shoe!”
“I will not,” retorted the Witch, “for it is now my shoe, and not yours.”
“You are a wicked creature!” cried Dorothy. “You have no right to take my shoe from me.”
“I shall keep it, just the same,” said the Witch, laughing at her, “and someday I shall get the other one from you, too.”
This made Dorothy so very angry that she picked up the bucket of water that stood near and dashed it over the Witch, wetting her from head to foot.
Instantly the wicked woman gave a loud cry of fear, and then, as Dorothy looked at her in wonder, the Witch began to shrink and fall away.
“See what you have done!” she screamed. “In a minute I shall melt away.”
“I’m very sorry, indeed,” said Dorothy, who was truly frightened to see the Witch actually melting away like brown sugar before her very eyes.
"""

ru_sample = """Маленькая девочка, увидев, что потеряла одну из своих красивых туфелек, рассердилась и сказала Ведьме: «Верни мне мою туфельку!»
«Я не буду, — парировала Ведьма, — потому что теперь это моя туфля, а не твоя».
«Ты злое существо!» - воскликнула Дороти. «Ты не имеешь права забирать у меня туфлю».
«Я все равно сохраню его, — сказала Ведьма, смеясь над ней, — и когда-нибудь я получу от тебя и другой».
Это так разозлило Дороти, что она взяла стоявшее рядом ведро с водой и облила им Ведьму, обмочив ее с головы до ног.
Мгновенно злая женщина громко вскрикнула от страха, а затем, когда Дороти с удивлением посмотрела на нее, Ведьма начала сжиматься и падать.
«Посмотри, что ты наделал!» она закричала. «Через минуту я растаю».
«Мне действительно очень жаль», — сказала Дороти, которая была по-настоящему напугана, увидев, что Ведьма тает, как коричневый сахар, у нее на глазах.
"""


class DataDir:
    """
    Creates a persistent data directory in data/tests_data/{dir_name} that will be
    cleaned out before a test run. This should help in persisting artifacts between test
    runs to manually verify the results.

    Taskcluster tasks can be run directly using the data dir via the run_task method.
    """

    def __init__(self, dir_name: str) -> None:
        self.path = os.path.join(TESTS_DATA, dir_name)

        # Ensure the base /data directory exists.
        os.makedirs(TESTS_DATA, exist_ok=True)

        # Clean up a previous run if this exists.
        if os.path.exists(self.path):
            shutil.rmtree(self.path)

        os.makedirs(self.path)
        print("Tests are using the subdirectory:", self.path)

    def join(self, name: str):
        """Create a folder or file name by joining it to the test directory."""
        return os.path.join(self.path, name)

    def load(self, name: str):
        """Load a text file"""
        with open(self.join(name), "r") as file:
            return file.read()

    def create_zst(self, name: str, contents: str) -> str:
        """
        Creates a compressed zst file and returns the path to it.
        """
        zst_path = os.path.join(self.path, name)
        if not os.path.exists(self.path):
            raise Exception(f"Directory for the compressed file does not exist: {self.path}")
        if os.path.exists(zst_path):
            raise Exception(f"A file already exists and would be overwritten: {zst_path}")

        # Create the compressed file.
        cctx = zstd.ZstdCompressor()
        compressed_data = cctx.compress(contents.encode("utf-8"))

        print("Writing a compressed file to: ", zst_path)
        with open(zst_path, "wb") as file:
            file.write(compressed_data)

        return zst_path

    def create_file(self, name: str, contents: str) -> str:
        """
        Creates a text file and returns the path to it.
        """
        text_path = os.path.join(self.path, name)
        if not os.path.exists(self.path):
            raise Exception(f"Directory for the text file does not exist: {self.path}")
        if os.path.exists(text_path):
            raise Exception(f"A file already exists and would be overwritten: {text_path}")

        print("Writing a text file to: ", text_path)
        with open(text_path, "w") as file:
            file.write(contents)

        return text_path

    def mkdir(self, name) -> str:
        path = self.join(name)
        os.makedirs(path, exist_ok=True)
        return path

    def run_task(
        self,
        task_name: str,
        work_dir: Optional[str] = None,
        fetches_dir: Optional[str] = None,
        env: dict[str, str] = {},
        extra_args: List[str] = None,
    ):
        """
        Runs a task from the taskgraph. See artifacts/full-task-graph.json after running a
        test for the full list of task names

        Arguments:

        task_name - The full task name like "split-mono-src-en"
            or "evaluate-backward-sacrebleu-wmt09-en-ru".

        data_dir - The test's DataDir

        work_dir - This is the TASK_WORKDIR, in tests generally the test's DataDir.

        fetches_dir - The MOZ_FETCHES_DIR, generally set as the test's DataDir.

        env - Any environment variable overrides.
        """

        command_parts, requirements, task_env = get_task_command_and_env(task_name)

        # There are some non-string environment variables that involve taskcluster references
        # Remove these.
        for key in task_env:
            if not isinstance(task_env[key], str):
                task_env[key] = ""

        current_folder = os.path.dirname(os.path.abspath(__file__))
        root_path = os.path.abspath(os.path.join(current_folder, "../.."))

        if not work_dir:
            work_dir = self.path
        if not fetches_dir:
            fetches_dir = self.path

        if extra_args:
            command_parts.extend(extra_args)

        final_env = {
            **os.environ,
            **task_env,
            "TASK_WORKDIR": work_dir,
            "MOZ_FETCHES_DIR": fetches_dir,
            "VCS_PATH": root_path,
            **env,
        }

        # Expand out environment variables in environment, for instance MARIAN=$MOZ_FETCHES_DIR
        # and FETCHES=./fetches will be expanded to MARIAN=./fetches
        for key, value in final_env.items():
            if not isinstance(value, str):
                continue
            expanded_value = final_env.get(value[1:])
            if value and value[0] == "$" and expanded_value:
                final_env[key] = expanded_value

        # Ensure the environment variables are sorted so that the longer variables get replaced first.
        sorted_env = sorted(final_env.items(), key=lambda kv: kv[0])
        sorted_env.reverse()

        for index, p in enumerate(command_parts):
            part = (
                p.replace("$TASK_WORKDIR/$VCS_PATH", root_path)
                .replace("$VCS_PATH", root_path)
                .replace("$TASK_WORKDIR", work_dir)
                .replace("$MOZ_FETCHES_DIR", fetches_dir)
            )

            # Apply the task environment.
            for key, value in sorted_env:
                env_var = f"${key}"
                if env_var in part:
                    part = part.replace(env_var, value)

            command_parts[index] = part

        # If using a venv, prepend the binary directory to the path so it is used.
        python_bin_dir = get_python_bin_dir(requirements)
        if python_bin_dir:
            final_env = {**final_env, "PATH": f'{python_bin_dir}:{os.environ.get("PATH", "")}'}
            if command_parts[0].endswith(".py"):
                # This script is relying on a shebang, add the python3 from the executable instead.
                command_parts.insert(0, os.path.join(python_bin_dir, "python3"))
        elif command_parts[0].endswith(".py"):
            # This script does not require a virtual environment.
            command_parts.insert(0, "python3")

        print("┌──────────────────────────────────────────────────────────")
        print("│ run_task:", " ".join(command_parts))
        print("└──────────────────────────────────────────────────────────")

        result = subprocess.run(
            command_parts,
            env=final_env,
            cwd=root_path,
            check=False,
        )
        fail_on_error(result)

    def print_tree(self):
        """
        Print a tree view of the data directory, which is useful for debugging test failures.
        """
        span_len = 90
        span = "─" * span_len
        print(f"┌{span}┐")

        for root, dirs, files in os.walk(self.path):
            level = root.replace(self.path, "").count(os.sep)
            indent = " " * 4 * (level)
            folder_text = f"│ {indent}{os.path.basename(root)}/"
            print(f"{folder_text.ljust(span_len)} │")
            subindent = " " * 4 * (level + 1)

            if len(files) == 0 and len(dirs) == 0:
                empty_text = f"│ {subindent} <empty folder>"
                print(f"{empty_text.ljust(span_len)} │")
            for file in files:
                file_text = f"│ {subindent}{file}"
                bytes = f"{os.stat(os.path.join(root, file)).st_size} bytes"

                print(f"{file_text.ljust(span_len - len(bytes))}{bytes} │")

        print(f"└{span}┘")


def fail_on_error(result: CompletedProcess[bytes]):
    """When a process fails, surface the stderr."""
    if not result.returncode == 0:
        raise Exception(f"{result.args[0]} exited with a status code: {result.returncode}")


# Only (lazily) create the full taskgraph once per test suite run as it's quite slow.
_full_taskgraph: Optional[dict[str, object]] = None


def get_full_taskgraph():
    """
    Generates the full taskgraph and stores it for re-use. It uses the config.pytest.yml
    in this directory.
    """
    global _full_taskgraph
    if _full_taskgraph:
        return _full_taskgraph

    start = time.time()

    current_folder = os.path.dirname(os.path.abspath(__file__))
    task_graph_json = os.path.join(current_folder, "../../artifacts/full-task-graph.json")
    config = os.path.join(current_folder, "config.pytest.yml")

    if os.environ.get("SKIP_TASKGRAPH"):
        print("Using existing taskgraph generation.")
    else:
        print(
            "Generating the full taskgraph, this can take a second. Set SKIP_TASKGRAPH=1 to skip this step."
        )
        run_taskgraph(config, get_taskgraph_parameters())

    with open(task_graph_json, "rb") as file:
        _full_taskgraph = json.load(file)

    elapsed_sec = time.time() - start
    print(f"Taskgraph generated in {elapsed_sec:.2f} seconds.")
    return _full_taskgraph


# Taskcluster commands can either be a single list of commands, or a nested list.
Commands = Union[list[str], list[list[str]]]


def get_command(commands: Commands) -> str:
    if isinstance(commands[-1], str):
        # Non-nested command, get the last string.
        return commands[-1]

    if isinstance(commands[-1][-1], str):
        # Nested command, get the last string of the last command.
        return commands[-1][-1]

    print(commands)
    raise Exception("Unable to find a string in the nested command.")


def find_pipeline_script(commands: Commands) -> str:
    """
    Extract the pipeline script and arguments from a command list.

    Commands take the form:
    [
       ['chmod', '+x', 'run-task'],
       ['./run-task', '--firefox_translations_training-checkout=./checkouts/vcs/', '--', 'bash', '-c', "full command"]
    ]

    or

    [
          "/usr/local/bin/run-task",
          "--firefox_translations_training-checkout=/builds/worker/checkouts/vcs/",
          "--", "bash", "-c",
          "full command"
    ]
    """
    command = get_command(commands)

    # Match a pipeline script like:
    #   pipeline/data/dataset_importer.py
    #   $VCS_PATH/taskcluster/scripts/pipeline/train-taskcluster.sh
    #   $VCS_PATH/pipeline/alignment/generate-alignment-and-shortlist.sh
    match = re.search(
        r"""
        # Script group:
        (?P<script>
            (?:python3?[ ])?   # Allow the script to be preceded by "python3 " or "python ".
            \$VCS_PATH         # "$VCS_PATH"
            [\w\/-]*           # Match any directories before "/pipeline/"
            \/pipeline\/       # "/pipeline/"
            [\w\/-]+           # Match any directories after "/pipeline/"
            \.(?:py|sh)        # Match the .sh, or .py extension
        )
        """,
        command,
        re.X,
    )

    if not match:
        raise Exception(f"Could not find a pipeline script in the command: {command}")

    script = match.group("script")

    # Split the parts of the command.
    command_parts = command.split(script)

    if len(command_parts) < 2:
        raise Exception(f"Could not find {script} in: {command}")

    # Remove the preamble to the script, which is should be the pip install.
    command_parts[0] = ""

    # Join the command parts back together to reassemble the command.
    return script.join(command_parts).strip()


def find_requirements(commands: Commands) -> Optional[str]:
    command = get_command(commands)

    # Match the following:
    # pip install -r $VCS_PATH/pipeline/eval/requirements/eval.txt && ...
    #                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    match = re.search(
        r"""
        pip3?\ install\ -r\ \$VCS_PATH\/  # Find the pip install.
        (?P<requirements>                 # Capture as "requirements"
            [\w\/\-\.]+                   # Match the path
        )
        """,
        command,
        re.X,
    )

    if match:
        return match.groupdict()["requirements"]

    return None


def get_task_command_and_env(task_name: str) -> tuple[list[str], Optional[str], dict[str, str]]:
    """
    Extracts a task's command from the full taskgraph. This allows for testing
    the full taskcluster pipeline and the scripts that it generates.
    See artifacts/full-task-graph.json for the full list of what is generated.

    task_name - The full task name like "split-mono-src-en"
        or "evaluate-backward-sacrebleu-wmt09-en-ru".
    """
    full_taskgraph = get_full_taskgraph()
    task = full_taskgraph.get(task_name)
    if not task:
        print("Available tasks:")
        for key in full_taskgraph.keys():
            print(f' - "{key}"')
        raise Exception(f"Could not find the task {task_name}")

    env = task["task"]["payload"]["env"]

    commands = task["task"]["payload"]["command"]
    pipeline_script = find_pipeline_script(commands)
    requirements = find_requirements(commands)

    print(f'Running: "{task_name}":')
    print(" > Commands:", commands)
    print(" > Running:", pipeline_script)
    print(" > Env:", env)
    print(" > Requirements:", requirements)

    command_parts = [
        part
        for part in shlex.split(pipeline_script)
        # subprocess.run doesn't understand how to redirect stderr to stdout, so ignore this
        # if it's part of the command.
        if part != "2>&1"
    ]

    # The python binary will be picked by the run_task abstraction.
    if command_parts[0] == "python" or command_parts[0] == "python3":
        command_parts = command_parts[1:]

    # Return the full command.
    return command_parts, requirements, env


def get_mocked_downloads() -> str:
    corpus_samples = os.path.abspath(os.path.join(FIXTURES_PATH, "../data/corpus_samples"))

    def get_path(name: str):
        return os.path.join(corpus_samples, name)

    return json.dumps(
        {
            "https://dl.fbaipublicfiles.com/flores101/dataset/flores101_dataset.tar.gz":
                get_path("flores101_dataset.tar.gz"),
            "https://object.pouta.csc.fi/OPUS-ELRC-3075-wikipedia_health/v1/moses/en-ru.txt.zip":
                get_path("en-ru.txt.zip"),
            "https://object.pouta.csc.fi/OPUS-ELRC-3075-wikipedia_health/v1/moses/ru-en.txt.zip":
                "404",
            "http://data.statmt.org/news-crawl/en/news.2021.en.shuffled.deduped.gz":
                get_path("pytest-dataset.en.gz"),
            "http://data.statmt.org/news-crawl/ru/news.2021.ru.shuffled.deduped.gz":
                get_path("pytest-dataset.ru.gz"),
            "https://storage.googleapis.com/releng-translations-dev/data/en-ru/pytest-dataset.en.zst":
                get_path("pytest-dataset.en.zst"),
            "https://storage.googleapis.com/releng-translations-dev/data/en-ru/pytest-dataset.ru.zst":
                get_path("pytest-dataset.ru.zst"),
        }
    )  # fmt: skip


def get_python_bin_dir(requirements: Optional[str]) -> Optional[str]:
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
        os.path.join(DATA_PATH, "task-venvs", f"{environment}-{requirements_stem}-{hash}")
    )
    python_bin_dir = os.path.join(venv_dir, "bin")
    python_bin = os.path.join(python_bin_dir, "python")

    # Create the venv only if it doesn't exist.
    if not os.path.exists(venv_dir):
        try:
            print("Creating virtual environment")
            subprocess.check_call(
                # Give the virtual environment access to the system site packages, as these
                # are installed via docker.
                ["python", "-m", "venv", "--system-site-packages", venv_dir],
            )

            print("Installing setuptools", requirements)
            subprocess.check_call(
                [python_bin, "-m", "pip", "install", "--upgrade", "setuptools", "pip"],
            )

            print("Installing", requirements)
            subprocess.check_call(
                [python_bin, "-m", "pip", "install", "-r", requirements],
            )
        except Exception as exception:
            print("Removing the venv due to an error in its creation.")
            shutil.rmtree(venv_dir)
            raise exception

    return python_bin_dir


def hash_file(hash: any, path: str):
    """
    Hash the contents of a file.
    """
    with open(path, "rb") as f:
        while chunk := f.read(4096):
            hash.update(chunk)

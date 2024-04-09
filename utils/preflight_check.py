#!/usr/bin/env python3
"""
Perform pre-flight checks for a training run. This script will exercise the taskgraph
and output information about the training steps, and how they are organized. This is
helpful when debugging and understanding pipeline changes, or when writing a training
config.

Usage:

    task preflight-check

    # Open the graph
    task preflight-check -- --open_graph

    # Only show one section, like the task_group.
    task preflight-check -- --only task_group
"""

import argparse
import http.server
import json
import os
import socket
import sys
import urllib
import webbrowser
from enum import Enum
from textwrap import dedent
from typing import Callable, Optional, Union

import taskgraph.actions
import taskgraph.parameters
from blessed import Terminal
from taskgraph.config import load_graph_config
from taskgraph.util import yaml

current_folder = os.path.dirname(os.path.abspath(__file__))
artifacts_folder = os.path.join(current_folder, "../artifacts")

term = Terminal()

# The parameters are a read only dict. The class is not exported, so this is a close
# approximation of the type.
Parameters = dict[str]

# The type for the dependency injection of webbrowser.open.
OpenInBrowser = Callable[[str], None]


def load_yml(filename: str) -> any:
    with open(filename) as f:
        return yaml.load_stream(f)


def get_taskgraph_parameters() -> Parameters:
    # These are required by taskgraph.
    os.environ["TASK_ID"] = "fake_id"
    os.environ["TASKCLUSTER_ROOT_URL"] = "https://firefox-ci-tc.services.mozilla.com"

    # Load taskcluster/config.yml
    graph_config = load_graph_config("taskcluster")

    # Add the project's taskgraph directory to the python path, and register
    # any extensions present.
    graph_config.register()

    parameters = taskgraph.parameters.load_parameters_file(None, strict=False)
    parameters.check()
    # Example parameters:
    # {
    #   'base_ref': '',
    #   'base_repository': 'git@github.com:mozilla/firefox-translations-training.git',
    #   'base_rev': '',
    #   'build_date': 1704894563,
    #   'build_number': 1,
    #   'do_not_optimize': [],
    #   'enable_always_target': True,
    #   'existing_tasks': {},
    #   'filters': ['target_tasks_method'],
    #   'head_ref': 'main',
    #   'head_repository': 'git@github.com:mozilla/firefox-translations-training.git',
    #   'head_rev': 'e48440fc2c52da770d0f652a32583eae3450766f',
    #   'head_tag': '',
    #   'level': '3',
    #   'moz_build_date': '20240110074923',
    #   'next_version': None,
    #   'optimize_strategies': None,
    #   'optimize_target_tasks': True,
    #   'owner': 'nobody@mozilla.com',
    #   'project': 'firefox-translations-training',
    #   'pushdate': 1704894563,
    #   'pushlog_id': '0',
    #   'repository_type': 'git',
    #   'target_tasks_method': 'default',
    #   'tasks_for': '',
    #   'training_config': { ... },
    #   'version': None
    # }
    return parameters


_last_config_path = None


def run_taskgraph(cfg_path: str, parameters: Parameters) -> None:
    # The callback can be a few standard things like "cancel" and "rerun". Custom actions
    # can be created in taskcluster/translations_taskgraph/actions/ such as the train action.
    callback = "train"
    cfg_path = os.path.realpath(cfg_path)
    global _last_config_path  # noqa: PLW0602
    if _last_config_path:
        if cfg_path != _last_config_path:
            raise Exception(
                "Changing the config paths and re-running run_taskgraph is not supported."
            )
        # Don't regenerate the taskgraph for tests, as this can be slow. It's likely that
        # tests will exercise this codepath.
        return
    input = load_yml(cfg_path)

    # This command outputs the stdout. Ignore it here.
    stdout = sys.stdout
    devnull = open(os.devnull, "w")
    sys.stdout = devnull

    # This invokes train_action in taskcluster/translations_taskgraph/actions/train.py
    taskgraph.actions.trigger_action_callback(
        task_group_id=None,
        task_id=None,
        input=input,
        callback=callback,
        parameters=parameters,
        root="taskcluster",
        test=True,
    )

    sys.stdout = stdout


def pretty_print_training_config(parameters: Parameters) -> None:
    text = dedent(
        f"""
        {term.yellow_underline("Training config (JSON)")}

        The training config in YAML gets converted to JSON, and can sometimes
        be interpreted incorrectly. Verify the config here.
        """
    )
    print(text)
    print(term.gray(json.dumps(parameters["training_config"], indent=2)))


def pretty_print_artifacts_dir() -> None:
    docs = {
        "actions.json": """
            Contains the valid actions, such as:
                "retrigger", "add-new-jobs", "rerun", "cancel", "cancel-all",
                "rebuild-cached-tasks", "retrigger-multiple)
        """,
        "full-task-graph.json": """
            The full list of every task, such as.
            {
               "alignments-en-ru": { ... },
               "all-en-ru-1": { ... },
               "bicleaner-opus-Books_v1-en-ru": { ... },
               ...
            }
        """,
        "label-to-taskid.json": """
            For example: {
              "alignments-en-ru": "CJwUWGPIQ4CdeinnE_NtNQ",
              "all-en-ru-1": "DjZKX9lkTvmQDbnmFtNOBg",
              "bicleaner-opus-Books_v1-en-ru": "fukq_91DQ4S9verrlipC1A",
              ...
             }
        """,
        "parameters.yml": """
            Given the .yml config, this is what is applied to generate the tasks.
        """,
        "runnable-jobs.json": """
            I'm not sure, but it appears to be build-* and fetch-* jobs? Maybe it's the
            first round of tasks that can be run?
        """,
        "target-tasks.json": """
            The dummy target for training, such as ["all-en-ru-1"]
        """,
        "task-graph.json": """
            The full task graph DAG. e.g.
            {
                "A6tejCuJSBmOeykhkUVZgw": {
                    ...
                    "dependencies": { ... },
                    "task": { ... }
                    ...
                }
                ...
            }

        """,
    }
    ignore = ["fetch-content", "run-task"]
    text = dedent(
        f"""
        {term.yellow_underline("Artifacts")}

        The pre-flight check outputs the full description of the tasks to the
        artifacts directory. This can be useful for verifying configuration of
        the run.

        {term.gray(" .")}"""
    )
    print(text)

    files = os.listdir(artifacts_folder)
    for i, file in enumerate(files):
        if file in ignore:
            continue

        doc_icon = " " if i + 1 == len(files) else "│"
        file_icon = "└──" if i + 1 == len(files) else "├──"
        doc_lines = dedent(docs.get(file, "")).split("\n")
        file_entry = term.underline(f"artifacts/{file}")

        print(term.white(f" {file_icon} {file_entry}"))
        for doc_line in doc_lines:
            print(f" {term.white(doc_icon)}     {term.gray(doc_line)}")


def get_free_port() -> int:
    # https://stackoverflow.com/questions/1365265/on-localhost-how-do-i-pick-a-free-port-number
    sock = socket.socket()
    sock.bind(("", 0))
    return sock.getsockname()[1]


waiting_for_request = True


def pretty_print_cmd(command: Optional[Union[list[str], list[list[str]]]]):
    """Pretty print the cmd. It could be a nested array."""
    if not command:
        return

    # Check for nested commands.
    if isinstance(command[0], list):
        for subcommand in command:
            # Recurse into the subcommand
            pretty_print_cmd(subcommand)
        return

    # This command is not useful to display.
    if " ".join(command) == "chmod +x run-task":
        return

    # Many commands are invoked by bash. Hide that in the output.
    # Example:
    #  ['/usr/local/bin/run-task', '--firefox_translations_training-checkout=/builds/worker/checkouts/vcs/',
    #   '--task-cwd', '/builds/worker/checkouts/vcs', '--', 'bash', '-cx', 'make validate-taskgraph']
    try:
        index = command.index("bash")
        print(command)
        command = command[index + 2 :]
    except ValueError:
        pass

    try:
        index = command.index("/builds/worker/checkouts")
        command = command[index + 2 :]
    except ValueError:
        pass

    # This is a bit of a hacky way to not create a newline for `--`.
    delimiter = "#-#-#-#-#-#-#-#-#-#-#-#"
    if delimiter in command:
        raise Exception("Delimiter found in command, change the delimiter")

    subcommands = []
    for subcommand in " ".join(command).split("&&"):
        subcommands.append(
            (
                subcommand
                # No newlines for `command.sh -- extra_args`.
                .replace("-- ", delimiter)
                # Remove whitespace.
                .strip()
                # Create newlines for flags.
                .replace("--", "\\\n      --")
                # Put the `--` back.
                .replace(delimiter, "-- ")
            )
        )

    command_text = "\n    ".join(subcommands)

    print(f"    {term.gray(command_text)}")


def pretty_print_task_graph() -> None:
    with open(os.path.join(artifacts_folder, "full-task-graph.json"), "rb") as file:
        taskGraph = json.load(file)

    text = dedent(
        f"""
        {term.yellow_underline("Task Commands")}

        The following is a full list of the tasks and their commands to run them.
        """
    )
    print(text)

    for key, value in taskGraph.items():
        print(f"{term.cyan_bold_underline(key)}")
        print(f"  {term.white_bold(value['task']['metadata']['description'])}")
        pretty_print_cmd(value["task"]["payload"].get("command"))


def serve_taskgraph_file(
    graph_url, open_graph: bool, persist_graph: bool, open_in_browser: OpenInBrowser
) -> None:
    """
    Serves the taskgraph file so that it can be opened in the taskcluster tools graph.
    """
    if not open_graph:
        text = dedent(
            f"""
            {term.yellow_underline("Visualization")}

            To open a visualization of the task add --open_graph to the arguments,
            or drag the file {term.white_underline("artifacts/task-graph.json")} into:

            {term.white_underline("https://gregtatum.github.io/taskcluster-tools/")}
            """
        )
        print(text)
        return
    port = get_free_port()
    json_url = f"http://localhost:{port}"
    graph_url_final = f"{graph_url}/?taskGraph={urllib.parse.quote(json_url)}"
    open_in_browser(graph_url_final)
    server = http.server.HTTPServer(("", port), ServeArtifactFile)
    if persist_graph:
        print("Serving the graph:", term.underline(graph_url_final))
        print("Hit Ctrl-C to exit")
    while (waiting_for_request or persist_graph) and open_in_browser is webbrowser.open:
        server.handle_request()

    text = dedent(
        f"""
        {term.yellow_underline("Visualization")}

        The taskgraph structure was opened in TaskCluster tools. This represents
        a graph of the relationships of the tasks that will be used in training.
        """
    )
    print(text)


class ServeArtifactFile(http.server.BaseHTTPRequestHandler):
    """Creates a one-time server that just serves one file."""

    def _set_headers(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def log_message(self, *args):
        # Disable server logging.
        pass

    def do_HEAD(self):
        self._set_headers()

    def do_GET(self):
        self._set_headers()
        task_graph_path = os.path.join(artifacts_folder, "task-graph.json")
        try:
            with open(task_graph_path, "rb") as file:
                self.wfile.write(file.read())
        except Exception as exception:
            print("Failed to serve the file", exception)
            pass
        global waiting_for_request  # noqa: PLW0603
        waiting_for_request = False


Choices = Enum(
    "Choices",
    [
        "task_group",
        "artifacts",
        "training_config",
        "graph",
    ],
)


def main(
    args: Optional[list[str]] = None, open_in_browser: OpenInBrowser = webbrowser.open
) -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,  # Preserves whitespace in the help text.
    )
    parser.add_argument(
        "--config",
        default="taskcluster/configs/config.prod.yml",
        type=str,
        help='The path to the training config. Defaults to "configs/tc.prod.yml"',
    )
    parser.add_argument(
        "--only",
        default=None,
        type=str,
        choices=[c.name for c in Choices],
        help="Only output one section",
    )
    parser.add_argument(
        "--open_graph", action="store_true", help="Open the graph visualization in a browser"
    )
    parser.add_argument(
        "--persist_graph", action="store_true", help="Keep serving the graph indefinitely"
    )
    parser.add_argument(
        "--graph_url",
        default="https://gregtatum.github.io/taskcluster-tools",
        help="Override the graph URL (for local testing)",
    )
    parsed_args = parser.parse_args(args)

    # Build the artifacts folder.
    parameters = get_taskgraph_parameters()
    run_taskgraph(parsed_args.config, get_taskgraph_parameters())

    choice = Choices[parsed_args.only] if parsed_args.only else None
    if choice == Choices.task_group:
        pretty_print_task_graph()
    elif choice == Choices.artifacts:
        pretty_print_artifacts_dir()
    elif choice == Choices.training_config:
        pretty_print_training_config(get_taskgraph_parameters())
    elif choice == Choices.graph:
        serve_taskgraph_file(
            parsed_args.graph_url,
            parsed_args.open_graph,
            parsed_args.persist_graph,
            open_in_browser,
        )
    elif choice is None:
        pretty_print_task_graph()
        pretty_print_artifacts_dir()
        pretty_print_training_config(parameters)
        serve_taskgraph_file(
            parsed_args.graph_url,
            parsed_args.open_graph,
            parsed_args.persist_graph,
            open_in_browser,
        )


if __name__ == "__main__":
    main()

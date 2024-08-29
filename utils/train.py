"""
Open up the train task from the CLI based on your current branch.

For example:

  task train -- --config configs/experiments-2024-H2/en-lt-experiments-2024-H2-hplt-nllb.yml
"""

import argparse
from pathlib import Path
import subprocess
import sys
from time import sleep
from github import Github
import taskcluster
import webbrowser
import pyperclip


def run(command: list[str]):
    return subprocess.run(command, capture_output=True, check=True, text=True).stdout.strip()


def check_if_pushed(branch: str) -> bool:
    remote_commit = run(["git", "rev-parse", f"origin/{branch}"])
    local_commit = run(["git", "rev-parse", branch])
    return local_commit == remote_commit


def get_decision_task_push(branch: str):
    g = Github()
    repo_name = "mozilla/firefox-translations-training"
    print(f'Looking up "{repo_name}"')
    repo = g.get_repo(repo_name)
    ref = f"heads/{branch}"

    print('Finding the "Decision Task (push)"')
    checks = repo.get_commit(ref).get_check_runs()
    decision_task = None
    for check in checks:
        if check.name == "Decision Task (push)":
            decision_task = check

    return decision_task


def get_task_group_id(task_url: str):
    """
    Look up the task group ID from a task url.

    e.g. https://firefox-ci-tc.services.mozilla.com/tasks/PhAMJTZBSmSeWStXbR72xA
    """
    task_id = task_url.split("/")[-1]

    print("Decision Task ID:", task_id)
    queue = taskcluster.Queue({"rootUrl": "https://firefox-ci-tc.services.mozilla.com"})
    task = queue.task(task_id)
    task_group_id = task["taskGroupId"]
    print("Train Action Group ID:", task_group_id)
    return task_group_id


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        # Preserves whitespace in the help text.
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument("--config", type=Path, required=True, help="Path the config")
    parser.add_argument(
        "--branch",
        type=str,
        required=False,
        help="The name of the branch, defaults to the current branch",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip the checks for the branch being up to date",
    )

    args = parser.parse_args()
    branch = args.branch

    if branch:
        print(f"Using --branch: {branch}")
    else:
        branch = run(["git", "branch", "--show-current"])
        print(f"Using current branch: {branch}")

    if check_if_pushed(branch):
        print(f"Branch '{branch}' is up to date with origin.")
    elif args.force:
        print(
            f"Branch '{branch}' is not fully pushed to origin, bypassing this check because of --force."
        )
    else:
        print(
            f"Error: Branch '{branch}' is not fully pushed to origin. Use --force or push your changes."
        )
        sys.exit(1)

    timeout = 10
    while True:
        decision_task = get_decision_task_push(branch)

        if decision_task:
            if decision_task.status == "completed" and decision_task.conclusion == "success":
                # The decision task is completed.
                break
            elif decision_task.status == "queued":
                print(f"Decision task is queued, trying again in {timeout} seconds")
            elif decision_task.status == "inprogress":
                print(f"Decision task is in progress, trying again in {timeout} seconds")
            else:
                # The task failed.
                print(
                    f'Decision task is "{decision_task.status}" with the conclusion "{decision_task.conclusion}"'
                )
                sys.exit(1)
        else:
            print(f"Decision task is not available, trying again in {timeout} seconds")

        sleep(timeout)

    task_group_id = get_task_group_id(decision_task.details_url)

    config: Path = args.config

    url = f"https://firefox-ci-tc.services.mozilla.com/tasks/groups/{task_group_id}"
    print(f"Opening {url}")

    with config.open("rt", encoding="utf-8") as file:
        print('The config has been copied to your clipboard. Select "Train" from the actions.')
        pyperclip.copy(file.read())

    webbrowser.open(url)


if __name__ == "__main__":
    main()

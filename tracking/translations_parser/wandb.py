import json
import os
from pathlib import Path
from typing import List

import wandb

import taskcluster
from translations_parser.parser import logger
from translations_parser.publishers import WandB
from translations_parser.utils import build_task_name, suffix_from_group


def add_wandb_arguments(parser):
    parser.add_argument(
        "--wandb-project",
        help="Publish the training run to a Weight & Biases project.",
        default=None,
    )
    parser.add_argument(
        "--wandb-artifacts",
        help="Directory containing training artifacts to publish on Weight & Biases.",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--wandb-group",
        help="Add the training run to a Weight & Biases group e.g. by language pair or experiment.",
        default=None,
    )
    parser.add_argument(
        "--wandb-run-name",
        help="Use a custom name for the Weight & Biases run.",
        default=None,
    )
    parser.add_argument(
        "--wandb-publication",
        action="store_true",
        help="Trigger publication on Weight & Biases. Disabled by default. Can be set though env variable WANDB_PUBLICATION=true|false",
        default=os.environ.get("WANDB_PUBLICATION", "false").lower() == "true",
    )
    parser.add_argument(
        "--taskcluster-secret",
        help="Taskcluster secret name used to store the Weight & Biases secret API Key.",
        type=str,
        default=os.environ.get("TASKCLUSTER_SECRET"),
    )
    parser.add_argument(
        "--tags",
        help="List of tags to use on Weight & Biases publication",
        type=str,
        default=["taskcluster"],
        nargs="+",
    )


def get_wandb_token(secret_name):
    """
    Retrieve the Weight & Biases token from Taskcluster secret
    """
    secrets = taskcluster.Secrets({"rootUrl": os.environ["TASKCLUSTER_PROXY_URL"]})

    try:
        wandb_secret = secrets.get(secret_name)
        return wandb_secret["secret"]["token"]
    except Exception as e:
        raise Exception(
            f"Weight & Biases secret API Key retrieved from Taskcluster is malformed: {e}"
        )


def get_wandb_names() -> tuple[str, str, str, str]:
    """
    Find the various names needed to publish on Weight & Biases using
    the taskcluster task & group payloads.

    Returns project, group, run names and the task group ID.
    """
    task_id = os.environ.get("TASK_ID")
    if not task_id:
        raise Exception("Weight & Biases name detection can only run in taskcluster")

    # Load task & group definition
    # CI task groups do not expose any configuration, so we must use default values
    queue = taskcluster.Queue({"rootUrl": os.environ["TASKCLUSTER_PROXY_URL"]})
    task = queue.task(task_id)
    _, task_name = build_task_name(task)
    group_id = task["taskGroupId"]
    task_group = queue.task(group_id)
    config = task_group.get("extra", {}).get("action", {}).get("context", {}).get("input")
    if config is None:
        logger.warn(
            f"Experiment configuration missing on {group_id} @ extra/action/context/input, fallback to CI values"
        )
        experiment = {
            "src": "ru",
            "trg": "en",
            "name": "ci",
        }
    else:
        experiment = config["experiment"]

    # Publish experiments triggered from the CI to a specific "ci" project
    if experiment["name"] == "ci":
        project = "ci"
    else:
        project = f'{experiment["src"]}-{experiment["trg"]}'

    return (
        project,
        f'{experiment["name"]}_{group_id}',
        task_name,
        group_id,
    )


def get_wandb_publisher(
    project_name=None,
    group_name=None,
    run_name=None,
    taskcluster_secret=None,
    artifacts=[],
    tags=[],
    logs_file=None,
    publication=False,
):
    if not publication:
        logger.info(
            "Skip weight & biases publication as requested by operator through WANDB_PUBLICATION"
        )
        return

    # Load secret from Taskcluster and auto-configure naming
    suffix = ""
    if taskcluster_secret:
        assert os.environ.get(
            "TASKCLUSTER_PROXY_URL"
        ), "When using `--taskcluster-secret`, `TASKCLUSTER_PROXY_URL` environment variable must be set too."

        # Weight and Biases client use environment variable to read the token
        os.environ.setdefault("WANDB_API_KEY", get_wandb_token(taskcluster_secret))

        project_name, group_name, run_name, task_group_id = get_wandb_names()
        suffix = suffix_from_group(task_group_id)

    # Enable publication on weight and biases when project is set
    # But prevent running when explicitly disabled by operator
    if not project_name:
        logger.info("Skip weight & biases publication as project name is not set")
        return

    # Build optional configuration with log file
    config = {}
    if logs_file:
        config["logs_file"] = logs_file

    # Automatically adds experiment owner to the tags
    if author := os.environ.get("WANDB_AUTHOR"):
        tags.append(f"author:{author}")

    return WandB(
        project=project_name,
        group=group_name,
        name=run_name,
        suffix=suffix,
        artifacts=artifacts,
        tags=tags,
        config=config,
    )


def list_existing_group_logs_metrics(
    wandb_run: wandb.sdk.wandb_run.Run,
) -> List[List[str | float]]:
    """Retrieve the data from groups_logs metric table"""
    if wandb_run.resumed is False:
        return []
    logger.info(f"Retrieving existing group logs metrics from group_logs ({wandb_run.id})")
    api = wandb.Api()
    run = api.run(f"{wandb_run.project}/{wandb_run.id}")
    last = next(
        (
            artifact
            for artifact in list(run.files())[::-1]
            if artifact.name.startswith("media/table/metrics")
        ),
        None,
    )
    if not last:
        return []
    data = json.load(last.download(replace=True))
    return data.get("data", [])

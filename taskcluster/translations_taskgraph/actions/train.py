# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from taskgraph.actions.registry import register_callback_action
from taskgraph.decision import taskgraph_decision
from taskgraph.parameters import Parameters

TRAIN_ON_PROJECTS = (
    "https://github.com/mozilla/firefox-translations-training",
    "https://github.com/mozilla-releng/staging-firefox-translations-training",
)


def can_train(parameters):
    return parameters["head_repository"] in TRAIN_ON_PROJECTS


@register_callback_action(
    name="train",
    title="Train",
    symbol="train",
    description="Initiate part or all of the training pipeline",
    generic=False,
    order=500,
    context=[],
    available=can_train,
    # TODO: investigate re-using the exact schema of the existing configs
    # for this both to ease the transition to taskcluster, and because they
    # have already been well thought out
    schema=lambda graph_config: {
        "type": "object",
        "properties": {
            "stage": {
                "type": "string",
                "description": """The stage of the pipeline to run until
(any stages this choice depends on will be automatically included).""",
                "default": "",
                # TODO: this should probably be specified in ci/config.yml
                "enum": ["clean", "bicleaner", "bicleaner-ai"],
            },
            "datasets": {
                "type": "array",
                "description": "The datasets to train with",
                "default": [],
                "items": {
                    "type": "string",
                    # TODO: pull this from ci/config.yml
                    "enum": ["flores-dev"],
                },
            },
            # TODO: should these be replaced with a single pair?
            "src_locale": {
                "type": "string",
                "description": "The src locale to train",
                "default": "",
            },
            "trg_locale": {
                "type": "string",
                "description": "The trg locale to train",
                "default": "",
            },
            # TODO: lots of reworking here. the default should be by dataset
            # we may want to re-use the existing pipeline configs, too
            "bicleaner_threshold": {
                "type": "string",
                "description": "bicleaner threshold",
                "default": "1.0",
            },
        },
        "required": [
            "stage",
            "datasets",
            "src_locale",
            "trg_locale",
        ],
    },
)
def train_action(parameters, graph_config, input, task_group_id, task_id):
    stage = input["stage"]
    target_datasets = input["datasets"]
    src_locale = input.get("src_locale")
    trg_locale = input.get("trg_locale")
    graph_config["datasets"]
    locale_str = f"{src_locale}-{trg_locale}"

    # TODO: Add a whack load of verification here. Things such as:
    # - datasets all exist
    # - locale pair exists for each dataset
    # - stage is valid
    # etc.

    parameters = dict(parameters)

    parameters["target_tasks_method"] = "train-target-tasks"

    # When doing staging releases, we still want to re-use tasks from previous
    # graphs.
    parameters["optimize_target_tasks"] = True
    parameters["tasks_for"] = "action"

    # make parameters read-only
    parameters["target_task_names"] = [f"{stage}-{d}-{locale_str}" for d in target_datasets]
    parameters["bicleaner_threshold"] = input["bicleaner_threshold"]
    parameters = Parameters(**parameters)

    taskgraph_decision({"root": graph_config.root_dir}, parameters=parameters)

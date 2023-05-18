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


# Stages that only have locales in their task names (not providers/datasets).
# Typically these are stages that "fan in" and a consume a number of upstream
# tasks that are per-dataset.
LOCALE_ONLY_STAGES = ["merge-corpus"]

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
                "enum": ["clean", "bicleaner", "bicleaner-ai", "merge-corpus", "train-vocab"],
            },
            "datasets": {
                "type": "object",
                "description": "The datasets to train with",
                "default": {},
                "properties": {
                    "train": {
                        "type": "array",
                        "description": "Parallel training corpus",
                        "default": [],
                        "items": {
                            "type": "string",
                            # TODO
                            # "enum": []
                        },
                    },
                    "devtest": {
                        "type": "array",
                        "description": "datasets to merge for validation while training",
                        "default": [],
                        "items": {
                            "type": "string",
                            # TODO
                            # "enum": []
                        },
                    },
                    "test": {
                        "type": "array",
                        "description": "datasets for evaluation",
                        "default": [],
                        "items": {
                            "type": "string",
                            # TODO
                            # "enum": []
                        },
                    },
                    "mono-src": {
                        "type": "array",
                        "description": """
monolingual datasets (ex. paracrawl-mono_paracrawl8, commoncrawl_wmt16, news-crawl_news.2020)
to be translated by the teacher model
""",
                        "default": [],
                        "items": {
                            "type": "string",
                            # TODO
                            # "enum": []
                        },
                    },
                    "mono-trg": {
                        "type": "array",
                        "description": """
to be translated by the backward model to augment teacher corpus with back-translations
leave empty to skip augmentation step (high resource languages)
""",
                        "default": [],
                        "items": {
                            "type": "string",
                            # TODO
                            # "enum": []
                        },
                    },
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
            "train_vocab_sample_size": {
                "type": "string",
                "description": "vocabularly training sample size",
                "default": "10000",
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

    # TODO: Add a whack load of verification here. Things such as:
    # - datasets all exist
    # - locale pair exists for each dataset
    # - stage is valid
    # etc.

    parameters = dict(parameters)

    parameters["target_tasks_method"] = "train-target-tasks"
    parameters["optimize_target_tasks"] = True
    parameters["tasks_for"] = "action"
    parameters["stage"] = input["stage"]
    parameters["datasets"] = input["datasets"]
    parameters["src_locale"] = input["src_locale"]
    parameters["trg_locale"] = input["trg_locale"]
    parameters["bicleaner_threshold"] = input["bicleaner_threshold"]
    parameters["train_vocab_sample_size"] = input["train_vocab_sample_size"]

    parameters = Parameters(**parameters)
    taskgraph_decision({"root": graph_config.root_dir}, parameters=parameters)

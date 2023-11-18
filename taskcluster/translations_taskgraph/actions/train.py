# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from taskgraph.actions.registry import register_callback_action
from taskgraph.decision import taskgraph_decision
from taskgraph.parameters import Parameters

from translations_taskgraph.parameters import get_defaults

TRAIN_ON_PROJECTS = (
    "https://github.com/mozilla/firefox-translations-training",
    "https://github.com/mozilla-releng/staging-firefox-translations-training",
)


def can_train(parameters):
    return parameters["head_repository"] in TRAIN_ON_PROJECTS


defaults = get_defaults("")["training_config"]


@register_callback_action(
    name="train",
    title="Train",
    symbol="train",
    description="Initiate part or all of the training pipeline",
    generic=False,
    order=500,
    context=[],
    available=can_train,
    schema=lambda graph_config: {
        "type": "object",
        "properties": {
            "target-stage": {
                "type": "string",
                "description": """The stage of the pipeline to run until
(any stages this choice depends on will be automatically included).""",
                "default": defaults["target-stage"],
                # TODO: this should probably be specified in ci/config.yml
                "enum": [
                    "clean-corpus",
                    "clean-mono",
                    "bicleaner",
                    "merge-corpus",
                    "merge-devset",
                    "merge-mono",
                    "train-vocab",
                    "train-backwards",
                    "evaluate-backwards",
                    "split-corpus",
                    "split-mono",
                    "translate-mono-trg",
                    "collect-mono-trg",
                    "train-teacher",
                    "evaluate-teacher",
                    "evaluate-finetuned-teacher",
                    "translate-corpus",
                    "extract-best",
                    "collect-corpus",
                    "translate-mono-src",
                    "collect-mono-src",
                    "merge-translated",
                    "score",
                    "cefilter",
                    "alignments",
                    "train-student",
                    "evaluate-student",
                    "finetune-student",
                    "evaluate-finetuned-student",
                    "quantize",
                    "evaluate-quantized",
                    "export",
                    "evaluate-teacher-ensemble",
                    "all",
                ],
            },
            "experiment": {
                "type": "object",
                "default": defaults["experiment"],
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "A name for the experiment",
                    },
                    "src": {
                        "type": "string",
                        "description": "The src locale to train",
                    },
                    "trg": {
                        "type": "string",
                        "description": "The trg locale to train",
                    },
                    "teacher-ensemble": {
                        "type": "number",
                        "description": "Number of teachers to train",
                    },
                    "backward-model": {
                        "type": "string",
                        "description": "???",
                    },
                    "vocab": {
                        "type": "string",
                        "description": "???",
                    },
                    "mono-max-sentences-src": {
                        "type": "number",
                        "description": "limits per downloaded src dataset",
                    },
                    "mono-max-sentences-trg": {
                        "type": "number",
                        "description": "limits per downloaded trg dataset",
                    },
                    "split-length": {
                        "type": "number",
                        "description": "???",
                    },
                    "spm-sample-size": {
                        "type": "number",
                        "description": "vocabularly training sample size",
                    },
                    "spm-vocab-size": {
                        "type": "number",
                        "description": "size of the vocabularly, can be reduced for testing",
                    },
                    "best-model": {
                        "type": "string",
                        "description": "best model to use for training",
                    },
                    "use-opuscleaner": {
                        "type": "string",
                        "description": "use OpusCleaner to clean corpus",
                    },
                    "bicleaner": {
                        "properties": {
                            "default-threshold": {
                                "type": "number",
                                "description": "bicleaner threshold",
                            },
                            "dataset-thresholds": {
                                "type": "object",
                                "additionalProperties": {
                                    "type": "number",
                                },
                            },
                        },
                        "required": [
                            "default-threshold",
                        ],
                    },
                },
                "required": [
                    "name",
                    "src",
                    "trg",
                    "bicleaner",
                ],
            },
            "marian-args": {
                "type": "object",
                "default": defaults["marian-args"],
                "properties": {
                    "training-backward": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "string",
                        },
                    },
                    "training-teacher": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "string",
                        },
                    },
                    "training-student": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "string",
                        },
                    },
                    "training-student-finetuned": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "string",
                        },
                    },
                    "decoding-backward": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "string",
                        },
                    },
                    "decoding-teacher": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "string",
                        },
                    },
                },
            },
            "datasets": {
                "type": "object",
                "default": defaults["datasets"],
                "description": "The datasets to train with",
                "properties": {
                    "train": {
                        "type": "array",
                        "description": "Parallel training corpus",
                        "items": {
                            "type": "string",
                            # TODO
                            # "enum": []
                        },
                    },
                    "devtest": {
                        "type": "array",
                        "description": "datasets to merge for validation while training",
                        "items": {
                            "type": "string",
                            # TODO
                            # "enum": []
                        },
                    },
                    "test": {
                        "type": "array",
                        "description": "datasets for evaluation",
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
                        "items": {
                            "type": "string",
                            # TODO
                            # "enum": []
                        },
                    },
                },
            },
            "taskcluster": {
                "type": "object",
                "default": defaults["taskcluster"],
                "description": "Taskcluster-specific pipeline configuration, eg: chunking",
                "properties": {
                    "split-chunks": {
                        "type": "number",
                        "description": "The number of chunks (parallel jobs) to use in `split` steps",
                    },
                },
            },
        },
        "required": [
            "target-stage",
            "datasets",
            "experiment",
            "marian-args",
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
    parameters["training_config"] = input

    parameters = Parameters(**parameters)
    taskgraph_decision({"root": graph_config.root_dir}, parameters=parameters)

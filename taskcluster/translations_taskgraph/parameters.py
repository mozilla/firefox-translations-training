# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from taskgraph.parameters import extend_parameters_schema
from voluptuous import Optional, Required


# These defaults line up with the `config.ci.yml` pipeline as much as possible.
# Their purpose is to provide a minimal config with a few datasets that can run
# the entire pipeline reasonably quickly to validate changes to the pipeline
# itself. Any real training should be overriding most, if not all, of these
# via the input to the `train` action.
def get_defaults(_):
    return {
        "training_config": {
            "target-stage": "all",
            "experiment": {
                "name": "ci",
                "src": "ru",
                "trg": "en",
                "teacher-ensemble": 1,
                # Used for providing a pretrained backward model. We do not support this yet.
                "backward-model": "NOT-YET-SUPPORTED",
                # Used for providing a pretrained vocab. We do not support this yet.
                "vocab": "NOT-YET-SUPPORTED",
                "mono-max-sentences-trg": 10000,
                "mono-max-sentences-src": 10000,
                "split-length": 5000,
                "spm-sample-size": 10000,
                "spm-vocab-size": 1000,
                "best-model": "chrf",
                "use-opuscleaner": "true",
                "bicleaner": {
                    "default-threshold": 0.5,
                    "dataset-thresholds": {
                        "opus_ada83/v1": 0.0,
                        "opus_ELRC-3075-wikipedia_health/v1": 0.6,
                    },
                },
            },
            "marian-args": {
                "training-backward": {
                    "disp-freq": "1",
                    "save-freq": "5",
                    "valid-freq": "10",
                    "after": "10u",
                    "dim-vocabs": "1000 1000",
                },
                "training-teacher": {
                    "disp-freq": "1",
                    "save-freq": "5",
                    "valid-freq": "10",
                    "after": "10u",
                    "dim-vocabs": "1000 1000",
                    "task": "transformer-base",
                },
                "training-student": {
                    "disp-freq": "1",
                    "save-freq": "5",
                    "valid-freq": "10",
                    "after": "10u",
                    "dim-vocabs": "1000 1000",
                },
                "training-student-finetuned": {
                    "disp-freq": "1",
                    "save-freq": "5",
                    "valid-freq": "10",
                    "after": "10u",
                    "dim-vocabs": "1000 1000",
                },
                "decoding-backward": {
                    "mini-batch-words": "2000",
                },
                "decoding-teacher": {
                    "mini-batch-words": "1000",
                    "precision": "float16",
                },
            },
            # These will never be used in practice, but specifying them ensures
            # that we always generate at least one task for each kind, which helps
            # to avoid bustage that doesn't show up until we run the training action.
            "datasets": {
                "train": [
                    "opus_ada83/v1",
                    "opus_ELRC-3075-wikipedia_health/v1",
                ],
                "devtest": [
                    "flores_dev",
                    "sacrebleu_aug-mix_wmt19",
                ],
                "test": [
                    "flores_devtest",
                ],
                "mono-src": [
                    "news-crawl_news.2008",
                ],
                "mono-trg": [
                    "news-crawl_news.2007",
                ],
            },
            # Taskcluster-specific configuration
            "taskcluster": {
                "split-chunks": 2,
            },
        },
    }


extend_parameters_schema(
    {
        Required("training_config"): {
            Required("target-stage"): str,
            Required("marian-args"): {
                Optional("training-backward"): {str: str},
                Optional("training-teacher"): {str: str},
                Optional("training-student"): {str: str},
                Optional("training-student-finetuned"): {str: str},
                Optional("decoding-backward"): {str: str},
                Optional("decoding-teacher"): {str: str},
            },
            Required("experiment"): {
                Required("name"): str,
                Required("src"): str,
                Required("trg"): str,
                Required("teacher-ensemble"): int,
                Required("backward-model"): str,
                Required("vocab"): str,
                Required("mono-max-sentences-trg"): int,
                Required("mono-max-sentences-src"): int,
                Required("split-length"): int,
                Required("spm-sample-size"): int,
                Optional("spm-vocab-size"): int,
                Required("best-model"): str,
                Required("use-opuscleaner"): str,
                Required("bicleaner"): {
                    Required("default-threshold"): float,
                    Optional("dataset-thresholds"): {
                        str: float,
                    },
                },
            },
            Optional("datasets"): {
                str: [str],
            },
            Optional("taskcluster"): {
                Optional("split-chunks"): int,
            },
        },
    },
    defaults_fn=get_defaults,
)


def deep_setdefault(dict_, defaults):
    for k, v in defaults.items():
        if isinstance(dict_.get(k), dict):
            deep_setdefault(dict_[k], defaults[k])
        else:
            dict_[k] = v


def get_decision_parameters(graph_config, parameters):
    parameters.setdefault("training_config", {})
    deep_setdefault(parameters, get_defaults(""))

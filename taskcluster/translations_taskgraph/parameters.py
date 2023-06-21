# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from taskgraph.parameters import extend_parameters_schema
from voluptuous import Optional, Required

# These defaults line up with the `config.test.yml` pipeline as much as possible.
# Their purpose is to provide a minimal config with a few datasets that can run
# the entire pipeline reasonably quickly to validate changes to the pipeline
# itself. Any real training should be overriding most, if not all, of these
# via the input to the `train` action.
def get_defaults(_):
    return {
        "training_config": {
            "target-stage": "score",
            "experiment": {
                "name": "training pipeline test config",
                "src": "ru",
                "trg": "en",
                "teacher-ensemble": 2,
                "backward-model": "",
                "vocab": "",
                "mono-max-sentences-trg": 200000,
                "mono-max-sentences-src": 100000,
                "split-length": 100000,
                "spm-sample-size": 100000,
                "best-model": "chrf",
                "bicleaner": {
                    "default-threshold": 0.5,
                    "dataset-thresholds": {
                        "opus_ada83/v1": 0.0,
                        "mtdata_Neulab-tedtalks_train-1-eng-rus": 0.6,
                    },
                },
            },
            "marian-args": {
                "training-backward": {
                    "disp-freq": "10",
                    "save-freq": "100",
                    "valid-freq": "100",
                    "after": "500u",
                },
                "training-teacher-base": {
                    "disp-freq": "10",
                    "save-freq": "100",
                    "valid-freq": "100",
                    "after": "500u",
                },
                "training-teacher-finetuned": {
                    "disp-freq": "10",
                    "save-freq": "100",
                    "valid-freq": "100",
                    "after": "500u",
                },
                "training-student": {
                    "disp-freq": "10",
                    "save-freq": "100",
                    "valid-freq": "100",
                    "after": "500u",
                },
                "training-student-finetuned": {
                    "disp-freq": "10",
                    "save-freq": "100",
                    "valid-freq": "100",
                    "after": "500u",
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
                    "opus_GNOME/v1",
                    "mtdata_Neulab-tedtalks_train-1-eng-rus",
                ],
                "devtest": [
                    "flores_dev",
                    "sacrebleu_wmt19",
                ],
                "test": [
                    "flores_devtest",
                    "sacrebleu_wmt20",
                ],
                "mono-src": [
                    "news-crawl_news.2020",
                ],
                "mono-trg": [
                    "news-crawl_news.2020",
                ],
            },
            # Taskcluster-specific configuration
            "taskcluster": {
                "split-chunks": 10,
            },
        },
    }

extend_parameters_schema(
    {
        Required("training_config"): {
            Required("target-stage"): str,
            Required("marian-args"): {
                Optional("training-backward"): {str: str},
                Optional("training-teacher-base"): {str: str},
                Optional("training-teacher-finetuned"): {str: str},
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
                Required("best-model"): str,
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
